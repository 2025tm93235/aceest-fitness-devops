"""Post-deployment checks against the Minikube ingress.

Run inside the test container after every Jenkins deployment:

    docker run --rm --network host -e INGRESS_IP=<minikube ip> \
        -e EXPECTED_VERSION=1.1.0 -e DEPLOY_STRATEGY=all <test-image> \
        python -m pytest deploy_tests -o addopts="" -v

A failing check makes Jenkins roll the deployment back.
"""

from __future__ import annotations

import json
import os
import urllib.request

import pytest

INGRESS_IP = os.environ.get("INGRESS_IP", "")
EXPECTED_VERSION = os.environ.get("EXPECTED_VERSION", "")
STRATEGY = os.environ.get("DEPLOY_STRATEGY", "all")
CANARY_WEIGHT = int(os.environ.get("CANARY_WEIGHT", "20"))

pytestmark = pytest.mark.skipif(not INGRESS_IP, reason="INGRESS_IP not set (no cluster)")


def health(host: str, headers: dict[str, str] | None = None) -> dict:
    request = urllib.request.Request(
        f"http://{INGRESS_IP}/health", headers={"Host": host, **(headers or {})}
    )
    with urllib.request.urlopen(request, timeout=5) as response:
        assert response.status == 200
        return json.loads(response.read())


def selected(strategy: str) -> bool:
    return STRATEGY in ("all", strategy)


def versions(host: str, count: int, headers: dict[str, str] | None = None) -> list[str]:
    return [health(host, headers)["version"] for _ in range(count)]


@pytest.mark.skipif(not selected("rolling"), reason="rolling update not deployed")
def test_rolling_update_serves_only_the_new_version():
    assert set(versions("rolling.aceest.local", 10)) == {EXPECTED_VERSION}


@pytest.mark.skipif(not selected("blue-green"), reason="blue-green not deployed")
def test_blue_green_live_colour_serves_the_new_version():
    body = health("bluegreen.aceest.local")
    assert body["version"] == EXPECTED_VERSION
    assert body["database"] == "ok"


@pytest.mark.skipif(not selected("canary"), reason="canary not deployed")
def test_canary_receives_a_share_of_traffic():
    seen = versions("canary.aceest.local", 60)
    assert len(set(seen)) <= 2, f"more than two versions behind the canary host: {set(seen)}"
    if CANARY_WEIGHT > 0:
        assert EXPECTED_VERSION in seen, "canary version never answered"


@pytest.mark.skipif(not selected("ab-test"), reason="A/B test not deployed")
def test_ab_variant_b_is_selected_by_header_and_cookie():
    assert set(versions("ab.aceest.local", 5, {"X-Variant": "B"})) == {EXPECTED_VERSION}
    assert set(versions("ab.aceest.local", 5, {"Cookie": "ab_variant=always"})) == {
        EXPECTED_VERSION
    }


@pytest.mark.skipif(not selected("shadow"), reason="shadow not deployed")
def test_shadow_host_is_served_by_stable():
    # Users always get the stable response; the mirrored copy goes to the
    # shadow deployment and is checked in its logs.
    body = health("shadow.aceest.local")
    assert body["status"] == "ok"


def test_production_url_is_healthy():
    assert health("aceest.local")["status"] == "ok"
