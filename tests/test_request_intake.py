"""Exercise the request composer through the same endpoints used by staff."""

import json
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from backend import departments
from backend.demo import make_principals
from backend.main import create_app, enable_demo_desks
from backend.store import initialize, transaction

API = '/v2/trade'


@pytest.fixture(scope='module')
def desk(tmp_path_factory):
    path = tmp_path_factory.mktemp('intake') / 'cases.sqlite'
    principals = {**make_principals(), **make_principals(specialists=True)}
    app = create_app(path, principals, mode='fixture')
    enable_demo_desks(app)
    with TestClient(app, base_url='http://127.0.0.1:8000', client=('127.0.0.1', 5050)) as client:
        forms = client.get(API + '/request-types').json()
        yield client, {f['id']: f for f in forms}, {v['role']: k for k, v in principals.items()}, path


def headers(desk, role, key=None):
    return {'Authorization': 'Bearer ' + desk[2][role], 'Idempotency-Key': key or str(uuid4())}


def submit(desk, f, example=0, key=None, **values):
    return desk[0].post(API + '/intake', headers=headers(desk, f['owner_role'], key),
                        json={**f['examples'][example], 'workflow_id': f['id'], **values})


def file(desk, cid, role):
    r = desk[0].get(API + '/cases/' + cid, headers=headers(desk, role))
    assert r.status_code == 200, r.text
    return r.json()


def packet(case):
    return {k: case[k] for k in ('revision', 'packet_hash')}


def post(desk, cid, role, action, body, key=None):
    return desk[0].post(f'{API}/cases/{cid}/{action}', headers=headers(desk, role, key), json=body)


def inbox(desk, cid, role):
    response = desk[0].get(API + '/cases', headers=headers(desk, role))
    assert response.is_success
    return next((case['my_approval'] for case in response.json() if case['case_id'] == cid), None)


@pytest.mark.parametrize('workflow', [departments.TRADE, *departments.CURRENT])
@pytest.mark.parametrize('example', [0, 1])
def test_each_form_submits_and_routes(desk, workflow, example):
    form = desk[1][workflow]
    data = form['examples'][example]
    response = submit(desk, form, example)
    assert response.status_code == 201, response.text
    cid = response.json()['case_id']
    case = file(desk, cid, form['owner_role'])
    assert case['last_run']['run_id'] == response.json()['run']['run_id']
    assert case['last_run']['status'] == 'sealed' and case['packet_hash']
    assert case['request_input'] == data and case['decision'] is None
    assert case['recommendation']['tone'] == ('review' if example == 0 else 'attention')
    plan = case['human_approval']
    assert plan['stage'] == 'ready' and plan['can_send'] and plan['final']['status'] == 'waiting'
    assert [p['id'] for p in plan['reviewers']] == [p['id'] for p in form['reviewers']]
    assert plan['final']['id'] == form['final']['id'] and plan['final']['id'] not in {p['id'] for p in plan['reviewers']}
    if example == 0:
        assert post(desk, cid, form['owner_role'], 'desk-review', packet(case)).status_code == 201
        sent = file(desk, cid, form['owner_role'])['human_approval']
        assert sent['stage'] == 'review' and not sent['can_send']
        assert all(p['status'] == 'awaiting' and p['sent_at'] for p in sent['reviewers'])
        assert sent['final']['sent_at'] is None


@pytest.mark.parametrize('workflow', [departments.TRADE, 'payments-cash-correspondent'])
def test_deliveries_require_named_people_and_a_human_final_decision(desk, workflow):
    form = desk[1][workflow]
    cid = submit(desk, form).json()['case_id']
    owner = form['owner_role']
    reviewers = [p['role'] for p in form['reviewers']]
    final = form['final']['role']
    signed = packet(file(desk, cid, owner))
    specialist = workflow != departments.TRADE
    reason = 'I checked the current synthetic record.'

    def review(role, **updates):
        if specialist:
            return post(desk, cid, role, 'workflow-action', {**signed, 'action': 'sign', 'reason': reason, **updates})
        return post(desk, cid, role, 'reviews/' + role,
                    {**signed, 'disposition': 'clear', 'reason_code': 'CHECKS_COMPLETE', 'reason': reason, **updates})

    def approve(role):
        if specialist:
            return post(desk, cid, role, 'workflow-action', {**signed, 'action': 'complete', 'reason': reason})
        return post(desk, cid, role, 'decision', {**signed, 'decision': 'approve', 'reason': reason})

    assert review(reviewers[0]).json()['code'] == 'approval_not_sent'
    assert inbox(desk, cid, reviewers[0]) is None
    assert post(desk, cid, final, 'desk-review', signed).status_code == 403
    assert post(desk, cid, owner, 'desk-review', {**signed, 'recipient_id': form['final']['id']}).status_code == 422
    assert post(desk, cid, owner, 'desk-review', {**signed, 'packet_hash': '0' * 64}).status_code == 409
    keys = [str(uuid4()), str(uuid4())]
    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(pool.map(lambda key: post(desk, cid, owner, 'desk-review', signed, key), keys))
    assert sorted(r.status_code for r in responses) == [200, 201]
    assert post(desk, cid, owner, 'desk-review', signed, keys[0]).json() == responses[0].json()
    initialize(desk[3], desk[0].app.state.principals)
    for role in reviewers:
        assert inbox(desk, cid, role) == 'review'
    assert inbox(desk, cid, final) is None and approve(final).status_code == 409
    assert inbox(desk, cid, 'coverage' if specialist else 'operations') is None

    for role in reviewers:
        assert inbox(desk, cid, final) is None
        signed_review = review(role)
        assert signed_review.status_code == 201, signed_review.text
        assert inbox(desk, cid, role) is None
    ready = file(desk, cid, final)
    assert ready['decision'] is None and ready['human_approval']['stage'] == 'decision'
    assert all(p['status'] == 'signed' for p in ready['human_approval']['reviewers'])
    assert ready['human_approval']['final']['status'] == 'awaiting' and inbox(desk, cid, final) == 'decision'
    assert approve(reviewers[0]).status_code == 403
    if specialist:
        partner = reviewers[-1]
        last_signature = next(r['event_id'] for r in ready['reviews'] if r['desk'] == partner)
        held = review(partner, action='hold', expected_event_id=last_signature)
        assert held.status_code == 201
        assert inbox(desk, cid, final) is None and approve(final).status_code == 409
        assert inbox(desk, cid, partner) == 'review'
        assert review(partner, expected_event_id=held.json()['event_id']).status_code == 201
        assert inbox(desk, cid, final) == 'decision'
    audit = desk[0].get(f'{API}/cases/{cid}/audit', headers=headers(desk, final)).json()
    assert [e['action'] for e in audit if e['action'].startswith('approval.')] == ['approval.review_sent', 'approval.decision_sent']
    assert approve(final).status_code == 201
    closed = file(desk, cid, final)
    assert closed['decision']['actor_id'] == form['final']['id'] and closed['human_approval']['final']['status'] == 'approve'
    assert inbox(desk, cid, final) is None


def test_preexisting_signed_and_unsent_packets_survive_upgrade(desk, monkeypatch):
    from backend import approvals

    form = desk[1]['payments-cash-correspondent']
    owner, approver = form['owner_role'], form['final']['role']
    # The previous release wrote signed reviews but had no delivery ledger.
    with monkeypatch.context() as previous:
        previous.setattr(approvals, 'require_delivery', lambda *args: None)
        previous.setattr(approvals, 'deliver', lambda *args: False)
        reviewed = submit(desk, form).json()['case_id']
        untouched = submit(desk, form).json()['case_id']
        signed = packet(file(desk, reviewed, owner))
        for reviewer in form['reviewers']:
            assert post(desk, reviewed, reviewer['role'], 'workflow-action',
                        {**signed, 'action': 'sign', 'reason': 'Checked the previous revision file.'}).status_code == 201
        seeded = desk[0].post(f"{API}/workflows/{form['id']}/cases", headers=headers(desk, owner), json={'example': 1}).json()['case_id']
        assert post(desk, seeded, owner, 'runs', {'revision': 1, 'mode': 'fixture'}).status_code == 202
    for _ in range(2):
        initialize(desk[3], desk[0].app.state.principals)
    assert inbox(desk, reviewed, approver) == 'decision' and file(desk, reviewed, approver)['decision'] is None
    assert file(desk, untouched, owner)['human_approval']['can_send'] and inbox(desk, untouched, owner) is None
    assert inbox(desk, seeded, owner) == 'review'
    with transaction(desk[3]) as db:
        events = db.execute("SELECT COUNT(*) FROM audit WHERE case_id=? AND action LIKE 'approval.%'", (reviewed,))
        assert events.fetchone()[0] == 2


def test_permissions_and_wrong_type_fields(desk):
    client, forms, *_ = desk
    assert len(forms) == 27
    assert len(client.get(API + '/request-types', headers=headers(desk, 'coverage')).json()) == 1
    assert client.get(API + '/request-types', headers=headers(desk, 'operations')).json() == []
    assert client.get(API + '/request-types', headers={'Origin': 'https://other.example'}).status_code == 401
    assert client.get(API + '/me', headers=headers(desk, 'coverage')).json()['desk_picker'] is False
    lc, hr = forms[departments.TRADE], next(f for f in forms.values() if f['code'] == 'HR')
    assert client.post(API + '/intake', headers=headers(desk, 'operations'), json={**lc['examples'][0], 'workflow_id': lc['id']}).status_code == 403
    for change in ({'amount_minor': None}, {'amount_minor': 0}, {'amount_minor': 1.5}, {'currency': 'EUR'}, {'requested_date': '2027-02-31'}, {'requested_date': '2020-01-01'}, {'customer_ref': 'another-customer'}, {'workflow_id': 'unknown'}):
        assert submit(desk, lc, **change).status_code in (404, 422)
    assert submit(desk, hr, amount_minor=1234, currency='EUR').status_code == 422


def test_custom_amount_and_replay(desk):
    form, key = desk[1][departments.TRADE], str(uuid4())
    changes = {'subject': 'Custom shipment', 'amount_minor': 250_000_051, 'notes': 'Desk-only shipping note', 'requested_date': '2027-02-04'}
    with ThreadPoolExecutor(max_workers=2) as pool:
        replies = list(pool.map(lambda _: submit(desk, form, key=key, **changes), range(2)))
    assert all(r.status_code == 201 for r in replies) and replies[0].json() == replies[1].json()
    cid = replies[0].json()['case_id']
    coverage, credit = file(desk, cid, 'coverage'), file(desk, cid, 'credit_risk')
    assert coverage['request_input']['subject'] == changes['subject'] and coverage['expiry'] == changes['requested_date']
    assert coverage['amount_minor'] == 250_000_051 and coverage['headroom_after_minor'] is None
    assert coverage['invoice_ref'] is None and coverage['invoice_document_id'] != form['examples'][0]['reference']
    assert coverage['recommendation']['title'] == 'Collect the supplier invoice'
    evidence = desk[0].post(API + '/cases/' + cid + '/evidence', headers=headers(desk, 'coverage'),
                            json={'fixture_document_id': form['examples'][0]['reference'], 'expected_revision': 1})
    assert evidence.status_code == 404
    assert credit['headroom_after_minor'] == -51 and credit['recommendation']['tone'] == 'attention'
    assert credit['request_input'] is None and changes['notes'] not in json.dumps(credit)
    assert submit(desk, form, key=key).status_code == 409
    with transaction(desk[3]) as db:
        assert db.execute('SELECT COUNT(*) FROM runs WHERE case_id=?', (cid,)).fetchone()[0] == 1
    referral = submit(desk, form, amount_minor=400_000_000).json()['case_id']
    assert 'higher credit' in file(desk, referral, 'coverage')['recommendation']['title']


def test_custom_reference_revision_and_local_projection(desk):
    f = next(f for f in desk[1].values() if f['code'] == 'PAY')
    marker = 'Staff-only case note'
    cid = submit(desk, f, subject='Returned transfer', reference='UNMATCHED-123', amount_minor=190001,
                 currency='GBP', notes=marker).json()['case_id']
    owner = file(desk, cid, f['owner_role'])
    assert not owner['department_case']['evidence_verified'] and owner['recommendation']['tone'] == 'attention'
    assert marker == owner['request_input']['notes']
    assert owner['case_title'] == 'Returned transfer' and owner['currency'] == 'GBP'
    partner = file(desk, cid, 'operations')
    assert partner['amount_minor'] is None and partner['case_title'] != 'Returned transfer'
    assert 'UNMATCHED-123' not in json.dumps(file(desk, cid, 'operations'))
    root = API + '/cases/' + cid
    assert marker not in desk[0].get(root + '/audit', headers=headers(desk, f['owner_role'])).text
    first = packet(owner)
    assert post(desk, cid, f['owner_role'], 'desk-review', first).status_code == 201
    assert inbox(desk, cid, 'operations') == 'review'
    assert desk[0].post(root + '/workflow-action', headers=headers(desk, f['owner_role']), json={'action': 'verify', 'revision': 1}).is_success
    revised = file(desk, cid, f['owner_role'])
    assert revised['recommendation'] is None and revised['request_input']['amount_minor'] == 190001
    assert any('analyst verified' in item['detail'] for item in revised['sources'])
    assert inbox(desk, cid, 'operations') is None and revised['human_approval']['stage'] == 'preparing'
    assert post(desk, cid, f['owner_role'], 'desk-review', first).json()['code'] == 'stale_revision'
    assert post(desk, cid, f['owner_role'], 'runs', {'revision': 2, 'mode': 'fixture'}).status_code == 202
    initialize(desk[3], desk[0].app.state.principals)
    new_packet = file(desk, cid, f['owner_role'])
    assert new_packet['human_approval']['can_send'] and inbox(desk, cid, 'operations') is None
    assert post(desk, cid, f['owner_role'], 'desk-review', packet(new_packet)).status_code == 201
    assert inbox(desk, cid, 'operations') == 'review'


def test_unavailable_run_does_not_issue_advice(desk, monkeypatch):
    from backend import integrations
    monkeypatch.setattr(integrations, 'prepare_packets', lambda *args, **kwargs: None)
    cid = submit(desk, desk[1][departments.TRADE]).json()['case_id']
    case = file(desk, cid, 'coverage')
    assert case['last_run']['status'] == 'analysis_unavailable' and case['recommendation'] is None
    assert not case['human_approval']['can_send']
    assert post(desk, cid, 'coverage', 'desk-review', {'revision': 1, 'packet_hash': '0' * 64}).status_code == 409


def test_request_text_stays_at_the_origin_and_out_of_model_turns(desk, monkeypatch):
    from backend import brane_client, integrations
    from backend.agent.runtime import ModelTurn
    from backend.request_intake import RequestInput, build

    monkeypatch.setattr(brane_client, 'live_run_config', lambda: ('example', 'example', 'test-policy', 'test'))
    sent = []

    def respond(**call):
        messages = call['messages']
        assert 'LOCAL-ONLY' not in json.dumps(messages) and '176543' not in json.dumps(messages)
        sent.append(call['task'])
        wording = json.loads(messages[-1]['content'])['wordings'][0]
        return ModelTurn('direct', json.dumps({'summary': wording}))

    monkeypatch.setattr(brane_client, 'send_turn', respond)
    pay = next(f for f in desk[1].values() if f['code'] == 'PAY')
    for f in (desk[1][departments.TRADE], pay):
        body = RequestInput(**{**f['examples'][0], 'workflow_id': f['id'], 'subject': 'LOCAL-ONLY subject',
                               'context': 'LOCAL-ONLY context', 'reference': 'LOCAL-ONLY record',
                               'amount_minor': 176543, 'notes': 'LOCAL-ONLY note'})
        s = build(body, departments.CURRENT.get(f['id']), f, 'ORG_DEMO_01')
        result = integrations.prepare_packets(s, 'live', run_id='TEST', authorize=lambda: None)
        assert result.status == 'prepared'
    assert len(sent) == 6
