"""HTML pages: login flow, CSRF protection, dashboard and programs."""

from __future__ import annotations

import re

import pytest

from tests.conftest import ADMIN_PASSWORD, ADMIN_USERNAME

CSRF_RE = re.compile(r'name="csrf_token" value="([^"]+)"')


def csrf(client, path="/login") -> str:
    match = CSRF_RE.search(client.get(path).get_data(as_text=True))
    assert match, f"no CSRF token on {path}"
    return match.group(1)


def web_login(client, password=ADMIN_PASSWORD, next_url=""):
    return client.post(
        "/login",
        data={
            "username": ADMIN_USERNAME,
            "password": password,
            "next": next_url,
            "csrf_token": csrf(client),
        },
    )


@pytest.fixture
def web_client(client):
    assert web_login(client).status_code == 302
    return client


def test_login_page_renders(client):
    response = client.get("/login")
    assert response.status_code == 200
    assert "ACEest Login" in response.get_data(as_text=True)


def test_dashboard_redirects_anonymous_users_to_login(client):
    response = client.get("/")
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login?next=/")


def test_successful_login_redirects_to_next(client):
    response = web_login(client, next_url="/programs")
    assert response.status_code == 302
    assert response.headers["Location"] == "/programs"


@pytest.mark.parametrize("next_url", ["https://evil.example", "//evil.example", "/\\evil", ""])
def test_login_ignores_unsafe_next(client, next_url):
    response = web_login(client, next_url=next_url)
    assert response.headers["Location"] == "/"


def test_failed_login_shows_error(client):
    response = web_login(client, password="nope")
    assert response.status_code == 401
    assert "Invalid username or password" in response.get_data(as_text=True)


def test_login_page_redirects_when_already_logged_in(web_client):
    assert web_client.get("/login").status_code == 302


def test_post_without_csrf_token_is_rejected(client):
    response = client.post("/login", data={"username": "admin", "password": "x"})
    assert response.status_code == 400


def test_post_with_wrong_csrf_token_is_rejected(client):
    csrf(client)  # creates a session token
    response = client.post("/login", data={"username": "a", "password": "b", "csrf_token": "x"})
    assert response.status_code == 400


def test_logout(web_client):
    response = web_client.post("/logout", data={"csrf_token": csrf(web_client, "/")})
    assert response.status_code == 302
    assert web_client.get("/").status_code == 302


def test_dashboard_lists_clients(web_client):
    web_client.post("/api/clients", json={"name": "Arun", "program": "beginner", "weight": 70})
    page = web_client.get("/").get_data(as_text=True)
    assert "Clients (1)" in page
    assert "Arun" in page
    assert "Beginner (BG)" in page
    assert "1820" in page  # 70 kg x 26


def test_dashboard_empty_state(web_client):
    assert "No clients yet" in web_client.get("/").get_data(as_text=True)


def test_create_client_via_form(web_client):
    response = web_client.post(
        "/clients",
        data={
            "csrf_token": csrf(web_client, "/"),
            "name": "Meena",
            "age": "31",
            "weight": "62.5",
            "program": "fat-loss-5day",
            "membership_status": "Active",
        },
        follow_redirects=True,
    )
    page = response.get_data(as_text=True)
    assert "Client Meena saved." in page
    assert web_client.get("/api/clients/Meena").get_json()["calories"] == 1500


def test_create_client_form_shows_validation_errors(web_client):
    response = web_client.post(
        "/clients",
        data={"csrf_token": csrf(web_client, "/"), "name": "", "age": "500"},
        follow_redirects=True,
    )
    page = response.get_data(as_text=True)
    assert "Name is required." in page
    assert "Age must be at most 120." in page


def test_programs_page_is_public(client):
    page = client.get("/programs").get_data(as_text=True)
    assert "Muscle Gain (MG) - PPL" in page
    assert "No day-by-day plan defined" in page  # 3-day fat loss variant


def test_api_error_on_web_route_renders_html(app, client):
    from aceest.errors import ApiError

    @app.get("/_web_boom")
    def boom():
        raise ApiError("Something went wrong", status=409)

    response = client.get("/_web_boom")
    assert response.status_code == 409
    assert response.mimetype == "text/html"
    assert "Something went wrong" in response.get_data(as_text=True)


# ------------------------------------------------------------- client page --
@pytest.fixture
def arun_page(web_client):
    web_client.post(
        "/api/clients",
        json={"name": "Arun", "height": 175, "weight": 80, "program": "muscle-gain-ppl"},
    )
    return web_client


def post_form(client, url, data):
    return client.post(url, data={"csrf_token": csrf(client, "/"), **data}, follow_redirects=True)


def test_dashboard_links_to_client_page(arun_page):
    assert 'href="/clients/Arun"' in arun_page.get("/").get_data(as_text=True)


def test_create_client_redirects_to_client_page(web_client):
    response = post_form(web_client, "/clients", {"name": "Bala"})
    assert "<h1>Bala</h1>" in response.get_data(as_text=True)


def test_client_page_shows_summary_and_bmi(arun_page):
    page = arun_page.get("/clients/Arun").get_data(as_text=True)
    assert "Muscle Gain (MG) - PPL" in page
    assert "2800 kcal/day" in page
    assert "26.1 (Overweight)" in page
    assert "No progress logged yet." in page


def test_client_page_without_bmi_data(web_client):
    web_client.post("/api/clients", json={"name": "Sam"})
    page = web_client.get("/clients/Sam").get_data(as_text=True)
    assert "Add height and weight to calculate BMI." in page


def test_unknown_client_page_returns_html_404(web_client):
    response = web_client.get("/clients/Ghost")
    assert response.status_code == 404
    assert "Client &#39;Ghost&#39; not found" in response.get_data(as_text=True)


def test_log_progress_via_form(arun_page):
    page = post_form(arun_page, "/clients/Arun/progress", {"adherence": "85"}).get_data(
        as_text=True
    )
    assert "Weekly progress logged." in page
    assert "width: 85%" in page


def test_invalid_progress_shows_error(arun_page):
    page = post_form(arun_page, "/clients/Arun/progress", {"adherence": "150"}).get_data(
        as_text=True
    )
    assert "Adherence must be at most 100." in page


def test_log_metrics_via_form(arun_page):
    page = post_form(
        arun_page, "/clients/Arun/metrics", {"date": "2026-05-01", "weight": "79.5", "waist": ""}
    ).get_data(as_text=True)
    assert "Metrics logged." in page
    assert "2026-05-01" in page


def test_log_workout_via_form_with_exercises(arun_page):
    page = post_form(
        arun_page,
        "/clients/Arun/workouts",
        {
            "date": "2026-05-02",
            "workout_type": "Strength",
            "duration_min": "70",
            "exercise_name_0": "Squat",
            "exercise_sets_0": "5",
            "exercise_reps_0": "5",
            "exercise_weight_0": "100",
            "exercise_name_1": "",
        },
    ).get_data(as_text=True)
    assert "Workout logged." in page
    assert "Squat 5x5 @ 100.0 kg" in page
    workouts = arun_page.get("/api/clients/Arun/workouts").get_json()["workouts"]
    assert len(workouts[0]["exercises"]) == 1


def test_invalid_workout_form_shows_errors(arun_page):
    page = post_form(
        arun_page,
        "/clients/Arun/workouts",
        {"workout_type": "Strength", "exercise_sets_0": "3"},
    ).get_data(as_text=True)
    assert "Exercises[0].name is required." in page


def test_generate_program_via_form_is_repeatable(arun_page):
    data = {"experience": "advanced", "seed": "11"}
    first = post_form(arun_page, "/clients/Arun/program", data).get_data(as_text=True)
    second = post_form(arun_page, "/clients/Arun/program", data).get_data(as_text=True)
    assert "Hypertrophy plan" in first
    assert "5 days/week" in first
    table = first.split("Hypertrophy plan")[1].split("</table>")[0]
    assert table == second.split("Hypertrophy plan")[1].split("</table>")[0]


def test_generate_program_form_validates(arun_page):
    page = post_form(arun_page, "/clients/Arun/program", {"experience": "guru"}).get_data(
        as_text=True
    )
    assert "Experience must be one of" in page


def test_update_profile_via_form(arun_page):
    page = post_form(
        arun_page,
        "/clients/Arun/update",
        {
            "name": "Arun Kumar",
            "weight": "82",
            "program": "beginner",
            "membership_status": "Active",
        },
    ).get_data(as_text=True)
    assert "Profile updated." in page
    assert "<h1>Arun Kumar</h1>" in page
    assert "2132 kcal/day" in page


def test_update_profile_validation_error(arun_page):
    page = post_form(arun_page, "/clients/Arun/update", {"name": "Arun", "age": "0"}).get_data(
        as_text=True
    )
    assert "Age must be at least 1." in page


def test_delete_client_via_form(arun_page):
    page = post_form(arun_page, "/clients/Arun/delete", {}).get_data(as_text=True)
    assert "Client Arun deleted." in page
    assert arun_page.get("/api/clients/Arun").status_code == 404


def test_client_pages_require_login(client):
    response = client.get("/clients/Arun")
    assert response.status_code == 302
    assert "/login?next=/clients/Arun" in response.headers["Location"]
