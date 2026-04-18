"""Playwright E2E tests for the Calculations CRUD flows.

Positive scenarios: create (all four operation types), retrieve (view page),
list (dashboard table), update (edit page), delete (dashboard and view page).

Negative scenarios: insufficient/invalid inputs (client-side), division by
zero (client-side and server-side), unauthenticated UI access (redirect to
login), unauthenticated API access (401), nonexistent resources (404 / error
state), cross-user access (404), invalid operation type (422).
"""

from uuid import uuid4

import pytest
import requests


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _base(fastapi_server: str) -> str:
    return fastapi_server.rstrip("/")


def _register_via_api(base_url: str, username: str, password: str) -> None:
    payload = {
        "first_name": "Test",
        "last_name": "User",
        "email": f"{username}@example.com",
        "username": username,
        "password": password,
        "confirm_password": password,
    }
    resp = requests.post(f"{base_url}/auth/register", json=payload)
    assert resp.status_code == 201, f"Pre-registration failed: {resp.text}"


def _login_via_api(base_url: str, username: str, password: str) -> str:
    resp = requests.post(
        f"{base_url}/auth/login",
        json={"username": username, "password": password},
    )
    assert resp.status_code == 200, f"Login failed: {resp.text}"
    return resp.json()["access_token"]


def _seed_user_and_login(base_url: str):
    """Register a fresh unique user and return (username, password, token)."""
    uid = uuid4().hex[:8]
    username = f"calcuser_{uid}"
    password = "ValidPass1!"
    _register_via_api(base_url, username, password)
    token = _login_via_api(base_url, username, password)
    return username, password, token


def _create_calculation_via_api(base_url: str, token: str, calc_type: str, inputs: list) -> dict:
    resp = requests.post(
        f"{base_url}/calculations",
        json={"type": calc_type, "inputs": inputs},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201, f"Calculation creation failed: {resp.text}"
    return resp.json()


def _set_auth(page, base_url: str, token: str, username: str = "TestUser") -> None:
    """Navigate to the app origin then inject the auth token into localStorage."""
    page.goto(base_url)
    page.wait_for_load_state("domcontentloaded")
    page.evaluate(f"localStorage.setItem('access_token', '{token}')")
    page.evaluate(f"localStorage.setItem('username', '{username}')")


# ===========================================================================
# POSITIVE SCENARIOS
# ===========================================================================

# ---------------------------------------------------------------------------
# Positive: Create addition calculation via dashboard UI
# ---------------------------------------------------------------------------
@pytest.mark.e2e
def test_create_calculation_addition_via_ui(page, fastapi_server):
    """Fill the dashboard form with an addition, submit, confirm 201 from the
    server, and verify the success alert contains the correct result (60)."""
    base = _base(fastapi_server)
    username, _, token = _seed_user_and_login(base)

    _set_auth(page, base, token, username)
    page.goto(f"{base}/dashboard")
    page.wait_for_load_state("domcontentloaded")

    page.select_option("#calcType", "addition")
    page.fill("#calcInputs", "10, 20, 30")

    with page.expect_response(
        lambda r: r.url.endswith("/calculations") and r.request.method == "POST"
    ) as resp_info:
        page.click('button[type="submit"]')

    resp = resp_info.value
    assert resp.status == 201, f"Expected 201, got {resp.status}: {resp.text()}"
    assert resp.json()["result"] == 60.0, (
        f"Expected result 60.0, got {resp.json()['result']}"
    )

    page.wait_for_selector("#successAlert:not(.hidden)", timeout=5000)
    success_text = page.inner_text("#successMessage")
    assert "60" in success_text, (
        f"Expected '60' in success message, got: {success_text!r}"
    )


# ---------------------------------------------------------------------------
# Positive: Create subtraction calculation via dashboard UI
# ---------------------------------------------------------------------------
@pytest.mark.e2e
def test_create_calculation_subtraction_via_ui(page, fastapi_server):
    """Submit a subtraction (100 − 30 − 20 = 50) through the dashboard form
    and verify the server returns 201 with the correct result."""
    base = _base(fastapi_server)
    username, _, token = _seed_user_and_login(base)

    _set_auth(page, base, token, username)
    page.goto(f"{base}/dashboard")
    page.wait_for_load_state("domcontentloaded")

    page.select_option("#calcType", "subtraction")
    page.fill("#calcInputs", "100, 30, 20")

    with page.expect_response(
        lambda r: r.url.endswith("/calculations") and r.request.method == "POST"
    ) as resp_info:
        page.click('button[type="submit"]')

    resp = resp_info.value
    assert resp.status == 201
    assert resp.json()["result"] == 50.0, (
        f"Expected result 50.0, got {resp.json()['result']}"
    )

    page.wait_for_selector("#successAlert:not(.hidden)", timeout=5000)


# ---------------------------------------------------------------------------
# Positive: Create multiplication calculation via dashboard UI
# ---------------------------------------------------------------------------
@pytest.mark.e2e
def test_create_calculation_multiplication_via_ui(page, fastapi_server):
    """Submit a multiplication (3 × 4 × 5 = 60) through the dashboard form
    and verify the server returns 201 with the correct result."""
    base = _base(fastapi_server)
    username, _, token = _seed_user_and_login(base)

    _set_auth(page, base, token, username)
    page.goto(f"{base}/dashboard")
    page.wait_for_load_state("domcontentloaded")

    page.select_option("#calcType", "multiplication")
    page.fill("#calcInputs", "3, 4, 5")

    with page.expect_response(
        lambda r: r.url.endswith("/calculations") and r.request.method == "POST"
    ) as resp_info:
        page.click('button[type="submit"]')

    resp = resp_info.value
    assert resp.status == 201
    assert resp.json()["result"] == 60.0, (
        f"Expected result 60.0, got {resp.json()['result']}"
    )

    page.wait_for_selector("#successAlert:not(.hidden)", timeout=5000)


# ---------------------------------------------------------------------------
# Positive: Create division calculation via dashboard UI
# ---------------------------------------------------------------------------
@pytest.mark.e2e
def test_create_calculation_division_via_ui(page, fastapi_server):
    """Submit a division (100 ÷ 4 = 25) through the dashboard form and verify
    the server returns 201 with the correct result."""
    base = _base(fastapi_server)
    username, _, token = _seed_user_and_login(base)

    _set_auth(page, base, token, username)
    page.goto(f"{base}/dashboard")
    page.wait_for_load_state("domcontentloaded")

    page.select_option("#calcType", "division")
    page.fill("#calcInputs", "100, 4")

    with page.expect_response(
        lambda r: r.url.endswith("/calculations") and r.request.method == "POST"
    ) as resp_info:
        page.click('button[type="submit"]')

    resp = resp_info.value
    assert resp.status == 201
    assert resp.json()["result"] == 25.0, (
        f"Expected result 25.0, got {resp.json()['result']}"
    )

    page.wait_for_selector("#successAlert:not(.hidden)", timeout=5000)


# ---------------------------------------------------------------------------
# Positive: Retrieve calculation via the view page
# ---------------------------------------------------------------------------
@pytest.mark.e2e
def test_retrieve_calculation_via_view_page(page, fastapi_server):
    """Create a calculation via the API, navigate to /dashboard/view/<id>,
    and confirm the details card shows the correct type and result."""
    base = _base(fastapi_server)
    username, _, token = _seed_user_and_login(base)

    calc = _create_calculation_via_api(base, token, "addition", [5.0, 10.0])
    calc_id = calc["id"]

    _set_auth(page, base, token, username)
    page.goto(f"{base}/dashboard/view/{calc_id}")
    page.wait_for_load_state("domcontentloaded")

    page.wait_for_selector("#calculationCard:not(.hidden)", timeout=10000)

    details_text = page.inner_text("#calcDetails")
    assert "addition" in details_text.lower(), (
        f"Expected 'addition' in details, got: {details_text!r}"
    )
    assert "15" in details_text, (
        f"Expected result '15' in details, got: {details_text!r}"
    )


# ---------------------------------------------------------------------------
# Positive: List calculations shown in dashboard table
# ---------------------------------------------------------------------------
@pytest.mark.e2e
def test_list_calculations_shown_in_dashboard_table(page, fastapi_server):
    """Create a calculation via the API, navigate to the dashboard, and confirm
    the history table displays the operation type and result."""
    base = _base(fastapi_server)
    username, _, token = _seed_user_and_login(base)

    _create_calculation_via_api(base, token, "multiplication", [7.0, 8.0])

    _set_auth(page, base, token, username)
    page.goto(f"{base}/dashboard")
    page.wait_for_load_state("domcontentloaded")

    page.wait_for_selector(".delete-calc", timeout=10000)

    table_text = page.inner_text("#calculationsTable")
    assert "multiplication" in table_text.lower(), (
        f"Expected 'multiplication' in table, got: {table_text!r}"
    )
    assert "56" in table_text, (
        f"Expected result '56' in table, got: {table_text!r}"
    )


# ---------------------------------------------------------------------------
# Positive: Update calculation via the edit page
# ---------------------------------------------------------------------------
@pytest.mark.e2e
def test_update_calculation_via_edit_page(page, fastapi_server):
    """Create an addition calculation, navigate to its edit page, change the
    inputs, submit, and confirm a 200 response with the updated result."""
    base = _base(fastapi_server)
    username, _, token = _seed_user_and_login(base)

    calc = _create_calculation_via_api(base, token, "addition", [1.0, 2.0])
    calc_id = calc["id"]

    _set_auth(page, base, token, username)
    page.goto(f"{base}/dashboard/edit/{calc_id}")
    page.wait_for_load_state("domcontentloaded")

    page.wait_for_selector("#editCard:not(.hidden)", timeout=10000)

    page.fill("#calcInputs", "50, 50")

    with page.expect_response(
        lambda r: f"/calculations/{calc_id}" in r.url and r.request.method == "PUT"
    ) as resp_info:
        page.click('button[type="submit"]')

    resp = resp_info.value
    assert resp.status == 200, (
        f"Expected 200 from PUT /calculations/{calc_id}, got {resp.status}: {resp.text()}"
    )
    assert resp.json()["result"] == 100.0, (
        f"Expected updated result 100.0, got {resp.json()['result']}"
    )

    page.wait_for_selector("#successAlert:not(.hidden)", timeout=5000)
    success_text = page.inner_text("#successMessage")
    assert "updated" in success_text.lower(), (
        f"Expected 'updated' in success message, got: {success_text!r}"
    )


# ---------------------------------------------------------------------------
# Positive: Delete calculation from the dashboard table
# ---------------------------------------------------------------------------
@pytest.mark.e2e
def test_delete_calculation_from_dashboard(page, fastapi_server):
    """Create a calculation via the API, navigate to the dashboard, click the
    Delete button, accept the confirmation dialog, and verify a 204 response
    and the success alert appears."""
    base = _base(fastapi_server)
    username, _, token = _seed_user_and_login(base)

    _create_calculation_via_api(base, token, "subtraction", [100.0, 40.0])

    _set_auth(page, base, token, username)
    page.goto(f"{base}/dashboard")
    page.wait_for_load_state("domcontentloaded")

    page.wait_for_selector(".delete-calc", timeout=10000)

    page.on("dialog", lambda d: d.accept())

    with page.expect_response(
        lambda r: "/calculations/" in r.url and r.request.method == "DELETE"
    ) as resp_info:
        page.click(".delete-calc")

    resp = resp_info.value
    assert resp.status == 204, f"Expected 204 from DELETE, got {resp.status}"

    page.wait_for_selector("#successAlert:not(.hidden)", timeout=5000)
    success_text = page.inner_text("#successMessage")
    assert "deleted" in success_text.lower(), (
        f"Expected 'deleted' in success message, got: {success_text!r}"
    )


# ---------------------------------------------------------------------------
# Positive: Delete calculation from the view page
# ---------------------------------------------------------------------------
@pytest.mark.e2e
def test_delete_calculation_from_view_page(page, fastapi_server):
    """Create a calculation via the API, navigate to its view page, click
    Delete, accept the confirmation dialog, and verify a 204 response and
    subsequent redirect to /dashboard."""
    base = _base(fastapi_server)
    username, _, token = _seed_user_and_login(base)

    calc = _create_calculation_via_api(base, token, "division", [200.0, 4.0])
    calc_id = calc["id"]

    _set_auth(page, base, token, username)
    page.goto(f"{base}/dashboard/view/{calc_id}")
    page.wait_for_load_state("domcontentloaded")

    page.wait_for_selector("#calculationCard:not(.hidden)", timeout=10000)

    page.on("dialog", lambda d: d.accept())

    with page.expect_response(
        lambda r: f"/calculations/{calc_id}" in r.url and r.request.method == "DELETE"
    ) as resp_info:
        page.click("#deleteBtn")

    resp = resp_info.value
    assert resp.status == 204, f"Expected 204 from DELETE, got {resp.status}"

    page.wait_for_url(f"**/dashboard", timeout=5000)
    assert "/dashboard" in page.url, (
        f"Expected redirect to /dashboard after delete, currently at {page.url}"
    )


# ===========================================================================
# NEGATIVE SCENARIOS
# ===========================================================================

# ---------------------------------------------------------------------------
# Negative: Create calculation with only one input → client-side error
# ---------------------------------------------------------------------------
@pytest.mark.e2e
def test_create_calculation_single_input_shows_client_error(page, fastapi_server):
    """Submit the dashboard form with only one number; client-side validation
    must show an error without making a server request."""
    base = _base(fastapi_server)
    username, _, token = _seed_user_and_login(base)

    _set_auth(page, base, token, username)
    page.goto(f"{base}/dashboard")
    page.wait_for_load_state("domcontentloaded")

    page.fill("#calcInputs", "42")
    page.click('button[type="submit"]')

    page.wait_for_selector("#errorAlert:not(.hidden)", timeout=3000)
    error_text = page.inner_text("#errorMessage")
    assert "two" in error_text.lower() or "numbers" in error_text.lower(), (
        f"Expected a 'two' or 'numbers' error message, got: {error_text!r}"
    )
    assert page.query_selector("#successAlert.hidden") is not None, (
        "Success alert should not be visible when validation fails"
    )


# ---------------------------------------------------------------------------
# Negative: Create calculation with empty inputs → client-side error
# ---------------------------------------------------------------------------
@pytest.mark.e2e
def test_create_calculation_empty_inputs_shows_client_error(page, fastapi_server):
    """Submit the dashboard form with no numbers; client-side validation must
    reject the submission without calling the server."""
    base = _base(fastapi_server)
    username, _, token = _seed_user_and_login(base)

    _set_auth(page, base, token, username)
    page.goto(f"{base}/dashboard")
    page.wait_for_load_state("domcontentloaded")

    page.fill("#calcInputs", "")
    page.click('button[type="submit"]')

    page.wait_for_selector("#errorAlert:not(.hidden)", timeout=3000)
    error_text = page.inner_text("#errorMessage")
    assert len(error_text) > 0, "Expected a non-empty error message for empty inputs"


# ---------------------------------------------------------------------------
# Negative: Update calculation with fewer than 2 inputs → client-side error
# ---------------------------------------------------------------------------
@pytest.mark.e2e
def test_update_calculation_single_input_shows_client_error(page, fastapi_server):
    """On the edit page, submit with only one number; client-side validation
    must show an error without calling the server."""
    base = _base(fastapi_server)
    username, _, token = _seed_user_and_login(base)

    calc = _create_calculation_via_api(base, token, "addition", [1.0, 2.0])
    calc_id = calc["id"]

    _set_auth(page, base, token, username)
    page.goto(f"{base}/dashboard/edit/{calc_id}")
    page.wait_for_load_state("domcontentloaded")

    page.wait_for_selector("#editCard:not(.hidden)", timeout=10000)

    page.fill("#calcInputs", "99")
    page.click('button[type="submit"]')

    page.wait_for_selector("#errorAlert:not(.hidden)", timeout=3000)
    error_text = page.inner_text("#errorMessage")
    assert "two" in error_text.lower() or "numbers" in error_text.lower(), (
        f"Expected validation error about needing at least two inputs, got: {error_text!r}"
    )


# ---------------------------------------------------------------------------
# Negative: Edit a division calculation with zero divisor → client-side error
# ---------------------------------------------------------------------------
@pytest.mark.e2e
def test_update_division_by_zero_shows_client_error(page, fastapi_server):
    """On the edit page for a division calculation, enter zero as a divisor;
    client-side validation must show a division-by-zero error."""
    base = _base(fastapi_server)
    username, _, token = _seed_user_and_login(base)

    calc = _create_calculation_via_api(base, token, "division", [100.0, 4.0])
    calc_id = calc["id"]

    _set_auth(page, base, token, username)
    page.goto(f"{base}/dashboard/edit/{calc_id}")
    page.wait_for_load_state("domcontentloaded")

    page.wait_for_selector("#editCard:not(.hidden)", timeout=10000)

    page.fill("#calcInputs", "100, 0")
    page.click('button[type="submit"]')

    page.wait_for_selector("#errorAlert:not(.hidden)", timeout=3000)
    error_text = page.inner_text("#errorMessage")
    assert "zero" in error_text.lower() or "division" in error_text.lower(), (
        f"Expected division-by-zero error, got: {error_text!r}"
    )


# ---------------------------------------------------------------------------
# Negative: Access /dashboard without auth token → redirect to /login
# ---------------------------------------------------------------------------
@pytest.mark.e2e
def test_dashboard_without_auth_redirects_to_login(page, fastapi_server):
    """Navigate to /dashboard with no token in localStorage; the client-side
    auth guard must immediately redirect to /login."""
    base = _base(fastapi_server)

    page.goto(f"{base}/")
    page.wait_for_load_state("domcontentloaded")
    page.evaluate("localStorage.clear()")

    page.goto(f"{base}/dashboard")
    page.wait_for_url("**/login", timeout=5000)
    assert "/login" in page.url, (
        f"Expected redirect to /login, currently at {page.url}"
    )


# ---------------------------------------------------------------------------
# Negative: Access /dashboard/view/<id> without auth token → redirect to /login
# ---------------------------------------------------------------------------
@pytest.mark.e2e
def test_view_page_without_auth_redirects_to_login(page, fastapi_server):
    """Navigate to a view-calculation page without a token; the auth guard
    must redirect to /login before any API call is made."""
    base = _base(fastapi_server)

    page.goto(f"{base}/")
    page.wait_for_load_state("domcontentloaded")
    page.evaluate("localStorage.clear()")

    page.goto(f"{base}/dashboard/view/{uuid4()}")
    page.wait_for_url("**/login", timeout=5000)
    assert "/login" in page.url, (
        f"Expected redirect to /login, currently at {page.url}"
    )


# ---------------------------------------------------------------------------
# Negative: Access /dashboard/edit/<id> without auth token → redirect to /login
# ---------------------------------------------------------------------------
@pytest.mark.e2e
def test_edit_page_without_auth_redirects_to_login(page, fastapi_server):
    """Navigate to an edit-calculation page without a token; the auth guard
    must redirect to /login before any API call is made."""
    base = _base(fastapi_server)

    page.goto(f"{base}/")
    page.wait_for_load_state("domcontentloaded")
    page.evaluate("localStorage.clear()")

    page.goto(f"{base}/dashboard/edit/{uuid4()}")
    page.wait_for_url("**/login", timeout=5000)
    assert "/login" in page.url, (
        f"Expected redirect to /login, currently at {page.url}"
    )


# ---------------------------------------------------------------------------
# Negative: View a nonexistent calculation → error state shown
# ---------------------------------------------------------------------------
@pytest.mark.e2e
def test_view_nonexistent_calculation_shows_error_state(page, fastapi_server):
    """Navigate to /dashboard/view/<fake-uuid> as an authenticated user; after
    the JS fetch returns 404 the 'Calculation Not Found' card must appear and
    the detail card must remain hidden."""
    base = _base(fastapi_server)
    username, _, token = _seed_user_and_login(base)

    _set_auth(page, base, token, username)
    page.goto(f"{base}/dashboard/view/{uuid4()}")
    page.wait_for_load_state("domcontentloaded")

    page.wait_for_selector("#errorState:not(.hidden)", timeout=10000)
    error_text = page.inner_text("#errorState")
    assert "not found" in error_text.lower() or "permission" in error_text.lower(), (
        f"Expected 'not found' or 'permission' message, got: {error_text!r}"
    )
    assert page.query_selector("#calculationCard.hidden") is not None, (
        "Calculation detail card should remain hidden when calculation does not exist"
    )


# ---------------------------------------------------------------------------
# Negative: Edit a nonexistent calculation → error state shown
# ---------------------------------------------------------------------------
@pytest.mark.e2e
def test_edit_nonexistent_calculation_shows_error_state(page, fastapi_server):
    """Navigate to /dashboard/edit/<fake-uuid> as an authenticated user; after
    the JS fetch returns 404 the 'Calculation Not Found' card must appear and
    the edit form must remain hidden."""
    base = _base(fastapi_server)
    username, _, token = _seed_user_and_login(base)

    _set_auth(page, base, token, username)
    page.goto(f"{base}/dashboard/edit/{uuid4()}")
    page.wait_for_load_state("domcontentloaded")

    page.wait_for_selector("#errorState:not(.hidden)", timeout=10000)
    error_text = page.inner_text("#errorState")
    assert "not found" in error_text.lower() or "permission" in error_text.lower(), (
        f"Expected 'not found' or 'permission' message, got: {error_text!r}"
    )
    assert page.query_selector("#editCard.hidden") is not None, (
        "Edit form card should remain hidden when calculation does not exist"
    )


# ---------------------------------------------------------------------------
# Negative: API — create calculation without Authorization header → 401
# ---------------------------------------------------------------------------
@pytest.mark.e2e
def test_create_calculation_api_unauthorized(fastapi_server):
    """POST /calculations without a token must return 401."""
    base = _base(fastapi_server)
    resp = requests.post(
        f"{base}/calculations",
        json={"type": "addition", "inputs": [1.0, 2.0]},
    )
    assert resp.status_code == 401, (
        f"Expected 401, got {resp.status_code}: {resp.text}"
    )


# ---------------------------------------------------------------------------
# Negative: API — list calculations without Authorization header → 401
# ---------------------------------------------------------------------------
@pytest.mark.e2e
def test_list_calculations_api_unauthorized(fastapi_server):
    """GET /calculations without a token must return 401."""
    base = _base(fastapi_server)
    resp = requests.get(f"{base}/calculations")
    assert resp.status_code == 401, (
        f"Expected 401, got {resp.status_code}: {resp.text}"
    )


# ---------------------------------------------------------------------------
# Negative: API — get single calculation without Authorization header → 401
# ---------------------------------------------------------------------------
@pytest.mark.e2e
def test_get_calculation_api_unauthorized(fastapi_server):
    """GET /calculations/<id> without a token must return 401."""
    base = _base(fastapi_server)
    resp = requests.get(f"{base}/calculations/{uuid4()}")
    assert resp.status_code == 401, (
        f"Expected 401, got {resp.status_code}: {resp.text}"
    )


# ---------------------------------------------------------------------------
# Negative: API — update calculation without Authorization header → 401
# ---------------------------------------------------------------------------
@pytest.mark.e2e
def test_update_calculation_api_unauthorized(fastapi_server):
    """PUT /calculations/<id> without a token must return 401."""
    base = _base(fastapi_server)
    resp = requests.put(
        f"{base}/calculations/{uuid4()}",
        json={"inputs": [5.0, 10.0]},
    )
    assert resp.status_code == 401, (
        f"Expected 401, got {resp.status_code}: {resp.text}"
    )


# ---------------------------------------------------------------------------
# Negative: API — delete calculation without Authorization header → 401
# ---------------------------------------------------------------------------
@pytest.mark.e2e
def test_delete_calculation_api_unauthorized(fastapi_server):
    """DELETE /calculations/<id> without a token must return 401."""
    base = _base(fastapi_server)
    resp = requests.delete(f"{base}/calculations/{uuid4()}")
    assert resp.status_code == 401, (
        f"Expected 401, got {resp.status_code}: {resp.text}"
    )


# ---------------------------------------------------------------------------
# Negative: API — create calculation with invalid operation type → 422
# ---------------------------------------------------------------------------
@pytest.mark.e2e
def test_create_calculation_invalid_type_returns_422(fastapi_server):
    """POST /calculations with an unrecognised operation type must return 422."""
    base = _base(fastapi_server)
    _, _, token = _seed_user_and_login(base)

    resp = requests.post(
        f"{base}/calculations",
        json={"type": "modulo", "inputs": [10.0, 3.0]},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 422, (
        f"Expected 422 for invalid type 'modulo', got {resp.status_code}: {resp.text}"
    )


# ---------------------------------------------------------------------------
# Negative: API — create calculation with only one input value → 422
# ---------------------------------------------------------------------------
@pytest.mark.e2e
def test_create_calculation_single_input_returns_422(fastapi_server):
    """POST /calculations with fewer than 2 inputs must return 422."""
    base = _base(fastapi_server)
    _, _, token = _seed_user_and_login(base)

    resp = requests.post(
        f"{base}/calculations",
        json={"type": "addition", "inputs": [42.0]},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 422, (
        f"Expected 422 for single input, got {resp.status_code}: {resp.text}"
    )


# ---------------------------------------------------------------------------
# Negative: API — create division by zero → 422
# ---------------------------------------------------------------------------
@pytest.mark.e2e
def test_create_division_by_zero_returns_422(fastapi_server):
    """POST /calculations for division with a zero divisor must return 422
    because the schema validator blocks division by zero."""
    base = _base(fastapi_server)
    _, _, token = _seed_user_and_login(base)

    resp = requests.post(
        f"{base}/calculations",
        json={"type": "division", "inputs": [10.0, 0.0]},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 422, (
        f"Expected 422 for division by zero, got {resp.status_code}: {resp.text}"
    )


# ---------------------------------------------------------------------------
# Negative: API — access another user's calculation → 404
# ---------------------------------------------------------------------------
@pytest.mark.e2e
def test_access_another_users_calculation_returns_404(fastapi_server):
    """Create a calculation as user A, then try to GET it as user B; the
    server must return 404 to prevent cross-user data access."""
    base = _base(fastapi_server)

    _, _, token_a = _seed_user_and_login(base)
    _, _, token_b = _seed_user_and_login(base)

    calc = _create_calculation_via_api(base, token_a, "addition", [5.0, 5.0])
    calc_id = calc["id"]

    resp = requests.get(
        f"{base}/calculations/{calc_id}",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert resp.status_code == 404, (
        f"Expected 404 when accessing another user's calculation, got {resp.status_code}: {resp.text}"
    )


# ---------------------------------------------------------------------------
# Negative: API — update another user's calculation → 404
# ---------------------------------------------------------------------------
@pytest.mark.e2e
def test_update_another_users_calculation_returns_404(fastapi_server):
    """Create a calculation as user A, then try to PUT it as user B; the
    server must return 404 to prevent cross-user modifications."""
    base = _base(fastapi_server)

    _, _, token_a = _seed_user_and_login(base)
    _, _, token_b = _seed_user_and_login(base)

    calc = _create_calculation_via_api(base, token_a, "multiplication", [3.0, 3.0])
    calc_id = calc["id"]

    resp = requests.put(
        f"{base}/calculations/{calc_id}",
        json={"inputs": [9.0, 9.0]},
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert resp.status_code == 404, (
        f"Expected 404 when updating another user's calculation, got {resp.status_code}: {resp.text}"
    )


# ---------------------------------------------------------------------------
# Negative: API — delete another user's calculation → 404
# ---------------------------------------------------------------------------
@pytest.mark.e2e
def test_delete_another_users_calculation_returns_404(fastapi_server):
    """Create a calculation as user A, then try to DELETE it as user B; the
    server must return 404 to prevent cross-user deletion."""
    base = _base(fastapi_server)

    _, _, token_a = _seed_user_and_login(base)
    _, _, token_b = _seed_user_and_login(base)

    calc = _create_calculation_via_api(base, token_a, "subtraction", [20.0, 5.0])
    calc_id = calc["id"]

    resp = requests.delete(
        f"{base}/calculations/{calc_id}",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert resp.status_code == 404, (
        f"Expected 404 when deleting another user's calculation, got {resp.status_code}: {resp.text}"
    )
