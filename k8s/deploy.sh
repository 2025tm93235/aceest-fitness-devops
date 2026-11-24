#!/usr/bin/env bash
# ACEest Fitness & Gym - Kubernetes deployment strategies and rollback.
#
# Usage:
#   bash k8s/deploy.sh setup                       # create namespace, volume, workloads, ingress (idempotent)
#   bash k8s/deploy.sh deploy   <strategy> <image> # roll out <image> with a strategy
#   bash k8s/deploy.sh promote  <strategy>         # canary / ab-test / shadow -> make the tested version stable
#   bash k8s/deploy.sh rollback <strategy>         # revert to the last stable version
#   bash k8s/deploy.sh status                      # images, live colour, canary weight
#
# Strategies: rolling | blue-green | canary | ab-test | shadow | all
#
# Environment:
#   NAMESPACE        (default aceest)
#   INGRESS_IP       (default: `minikube ip`)
#   CANARY_WEIGHT    percentage of canary.aceest.local traffic for a new canary (default 20)
#   ROLLOUT_TIMEOUT  (default 180s)
#   DEPLOYED_FILE    file that records which strategies were deployed (used for rollback)
#   CHANGE_CAUSE     text stored in the rollout history (default: "deploy <image>")
set -euo pipefail

NAMESPACE="${NAMESPACE:-aceest}"
CANARY_WEIGHT="${CANARY_WEIGHT:-20}"
ROLLOUT_TIMEOUT="${ROLLOUT_TIMEOUT:-180s}"
DEPLOYED_FILE="${DEPLOYED_FILE:-/dev/null}"
MANIFEST_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ALL_STRATEGIES=(rolling blue-green canary ab-test shadow)

k() { kubectl -n "${NAMESPACE}" "$@"; }
log() { printf '\n==> %s\n' "$*"; }
die() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }

ingress_ip() {
    if [[ -z "${INGRESS_IP:-}" ]]; then
        INGRESS_IP="$(minikube ip)"
    fi
    printf '%s' "${INGRESS_IP}"
}

# GET /health through the ingress for a host; retries while pods settle.
check_host() {
    local host="$1" ip attempt
    ip="$(ingress_ip)"
    for attempt in $(seq 1 12); do
        if curl -fsS --max-time 5 -H "Host: ${host}" "http://${ip}/health"; then
            echo
            return 0
        fi
        echo "  ${host} not ready yet (attempt ${attempt}/12)"
        sleep 5
    done
    return 1
}

image_of() {
    k get deployment "$1" -o jsonpath='{.spec.template.spec.containers[?(@.name=="app")].image}'
}

# Update one deployment's image and wait; undo automatically if the rollout fails.
set_image() {
    local deployment="$1" image="$2"
    log "Updating ${deployment} -> ${image}"
    k set image "deployment/${deployment}" "app=${image}"
    k annotate "deployment/${deployment}" --overwrite \
        "kubernetes.io/change-cause=${CHANGE_CAUSE:-deploy ${image}}"
    if ! k rollout status "deployment/${deployment}" --timeout="${ROLLOUT_TIMEOUT}"; then
        echo "Rollout of ${deployment} failed - rolling back to the previous revision"
        k rollout undo "deployment/${deployment}"
        k rollout status "deployment/${deployment}" --timeout="${ROLLOUT_TIMEOUT}" || true
        return 1
    fi
}

set_canary_weight() {
    log "Canary weight -> $1%"
    k annotate ingress aceest-canary --overwrite "nginx.ingress.kubernetes.io/canary-weight=$1"
}

live_colour() {
    k get service aceest-bluegreen -o jsonpath='{.spec.selector.track}'
}

point_services() {
    local live="$1" idle="$2"
    k patch service aceest-bluegreen -p "{\"spec\":{\"selector\":{\"track\":\"${live}\"}}}"
    k patch service aceest-bluegreen-preview -p "{\"spec\":{\"selector\":{\"track\":\"${idle}\"}}}"
}

record() { echo "$1" >>"${DEPLOYED_FILE}"; }

# ------------------------------------------------------------------ setup --
setup() {
    log "Applying namespace and storage"
    kubectl apply -f "${MANIFEST_DIR}/00-namespace.yaml" -f "${MANIFEST_DIR}/01-storage.yaml"
    k get secret aceest-secrets >/dev/null 2>&1 \
        || die "secret aceest-secrets is missing - create it first (see docs/KUBERNETES.md)"
    # Workloads and the resources the scripts mutate (service selectors,
    # canary weight, images) are created only once so a re-run never resets
    # a live colour or a deployed version.
    local file
    for file in "${MANIFEST_DIR}"/[1-3]*.yaml "${MANIFEST_DIR}"/40-ingress.yaml; do
        log "Ensuring $(basename "${file}")"
        kubectl create -f "${file}" 2>&1 | grep -v 'AlreadyExists' || true
    done
    log "Waiting for all deployments"
    local deployment
    for deployment in $(k get deployments -o name); do
        k rollout status "${deployment}" --timeout=300s
    done
}

# ----------------------------------------------------------------- deploy --
# Each strategy is recorded as soon as live traffic can see the new version,
# so a failed check afterwards is rolled back by `rollback`.
deploy_rolling() {
    set_image aceest-rolling "$1"
    record rolling
    check_host rolling.aceest.local
}

deploy_blue_green() {
    local image="$1" live idle
    live="$(live_colour)"
    if [[ "${live}" == "blue" ]]; then idle=green; else idle=blue; fi
    log "Blue-green: live=${live}, deploying to idle=${idle}"
    set_image "aceest-${idle}" "${image}"
    point_services "${live}" "${idle}"
    log "Testing the idle colour through bluegreen-preview.aceest.local"
    check_host bluegreen-preview.aceest.local || { echo "Preview check failed - live traffic untouched"; return 1; }
    log "Switching live traffic ${live} -> ${idle}"
    point_services "${idle}" "${live}"
    k annotate service aceest-bluegreen --overwrite "aceest.io/previous-track=${live}"
    record blue-green
    check_host bluegreen.aceest.local
}

deploy_canary() {
    set_canary_weight 0
    set_image aceest-canary "$1"
    set_canary_weight "${CANARY_WEIGHT}"
    record canary
    check_host canary.aceest.local
}

deploy_ab_test() {
    set_image aceest-variant-b "$1"
    record ab-test
    check_host ab.aceest.local
}

deploy_shadow() {
    set_image aceest-shadow "$1"
    record shadow
    check_host shadow.aceest.local
}

deploy() {
    local strategy="$1" image="$2"
    case "${strategy}" in
        rolling) deploy_rolling "${image}" ;;
        blue-green) deploy_blue_green "${image}" ;;
        canary) deploy_canary "${image}" ;;
        ab-test) deploy_ab_test "${image}" ;;
        shadow) deploy_shadow "${image}" ;;
        all) for s in "${ALL_STRATEGIES[@]}"; do deploy "${s}" "${image}"; done ;;
        *) die "unknown strategy '${strategy}'" ;;
    esac
}

# ---------------------------------------------------------------- promote --
promote() {
    local strategy="$1" source
    case "${strategy}" in
        canary) source=aceest-canary ;;
        ab-test) source=aceest-variant-b ;;
        shadow) source=aceest-shadow ;;
        rolling | blue-green) echo "${strategy}: nothing to promote (already live)"; return 0 ;;
        all) promote canary; return 0 ;;
        *) die "unknown strategy '${strategy}'" ;;
    esac
    local image
    image="$(image_of "${source}")"
    log "Promoting ${source} (${image}) to stable"
    CHANGE_CAUSE="promote ${image} from ${source}" set_image aceest-stable "${image}"
    if [[ "${strategy}" == "canary" ]]; then set_canary_weight 0; fi
    check_host aceest.local
}

# --------------------------------------------------------------- rollback --
rollback() {
    local strategy="$1"
    case "${strategy}" in
        rolling)
            log "Rolling update: undo to the previous revision"
            k rollout undo deployment/aceest-rolling
            k rollout status deployment/aceest-rolling --timeout="${ROLLOUT_TIMEOUT}"
            ;;
        blue-green)
            local live previous
            live="$(live_colour)"
            if [[ "${live}" == "blue" ]]; then previous=green; else previous=blue; fi
            log "Blue-green: switching live traffic back ${live} -> ${previous}"
            point_services "${previous}" "${live}"
            ;;
        canary)
            set_canary_weight 0
            k rollout undo deployment/aceest-canary
            k rollout status deployment/aceest-canary --timeout="${ROLLOUT_TIMEOUT}"
            ;;
        ab-test)
            k rollout undo deployment/aceest-variant-b
            k rollout status deployment/aceest-variant-b --timeout="${ROLLOUT_TIMEOUT}"
            ;;
        shadow)
            k rollout undo deployment/aceest-shadow
            k rollout status deployment/aceest-shadow --timeout="${ROLLOUT_TIMEOUT}"
            ;;
        all) for s in "${ALL_STRATEGIES[@]}"; do rollback "${s}"; done ;;
        *) die "unknown strategy '${strategy}'" ;;
    esac
}

# ----------------------------------------------------------------- status --
status() {
    log "Deployments"
    k get deployments -o custom-columns='NAME:.metadata.name,READY:.status.readyReplicas,IMAGE:.spec.template.spec.containers[0].image'
    log "Blue-green: live colour = $(live_colour)"
    log "Canary weight = $(k get ingress aceest-canary -o jsonpath='{.metadata.annotations.nginx\.ingress\.kubernetes\.io/canary-weight}')%"
    log "Ingress hosts (map to $(ingress_ip) in /etc/hosts)"
    k get ingress
}

main() {
    local action="${1:-}"
    case "${action}" in
        setup) setup ;;
        deploy) [[ $# -eq 3 ]] || die "usage: deploy <strategy> <image>"; deploy "$2" "$3" ;;
        promote) [[ $# -eq 2 ]] || die "usage: promote <strategy>"; promote "$2" ;;
        rollback) [[ $# -eq 2 ]] || die "usage: rollback <strategy>"; rollback "$2" ;;
        status) status ;;
        *) sed -n '2,20p' "${BASH_SOURCE[0]}"; exit 2 ;;
    esac
}

main "$@"
