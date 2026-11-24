// ACEest Fitness & Gym - Jenkins CI/CD pipeline
//
// Pulls the latest code from GitHub (SCM polling) and runs a clean, fully
// containerised build on the lab VM:
//   Checkout (clean workspace) -> Version -> Build test image -> Lint & compile
//   -> Unit tests in container (JUnit + coverage)
//   -> SonarQube analysis with blocking quality gate
//   -> Build runtime image -> Smoke test -> Push versioned image to Docker Hub
//   -> Build artifacts (build-info.json, source archive, reports)
//   -> Deploy to Minikube (rolling, blue-green, canary, A/B, shadow)
//   -> Post-deploy tests in the test container -> automatic rollback on failure
//
// Manual runs (Build with Parameters) can also promote a canary/A/B/shadow
// version to stable or roll a strategy back without rebuilding.
//
// Everything runs inside Docker, so the agent only needs Git and Docker;
// the host Python version does not matter.

pipeline {
    agent any

    options {
        timestamps()
        timeout(time: 45, unit: 'MINUTES')
        buildDiscarder(logRotator(numToKeepStr: '20'))
        disableConcurrentBuilds()
        skipDefaultCheckout(true)
    }

    parameters {
        choice(
            name: 'ACTION',
            choices: ['deploy', 'promote', 'rollback'],
            description: 'deploy = build, test, push and deploy this commit (default for SCM-triggered builds); promote / rollback = act on the cluster only.'
        )
        choice(
            name: 'DEPLOY_STRATEGY',
            choices: ['all', 'rolling', 'blue-green', 'canary', 'ab-test', 'shadow'],
            description: 'Deployment strategy to use (all = every strategy).'
        )
        string(
            name: 'CANARY_WEIGHT',
            defaultValue: '20',
            description: 'Percentage of canary.aceest.local traffic sent to a new canary.'
        )
        booleanParam(
            name: 'RUN_SONAR',
            defaultValue: true,
            description: 'Run SonarQube analysis and enforce its Quality Gate (requires the SonarQube server "sonarqube" and scanner tool "SonarScanner" to be configured in Jenkins).'
        )
    }

    triggers {
        // Poll GitHub every ~2 minutes and build only when new commits exist.
        // Works without exposing Jenkins to the internet. If GitHub can reach
        // this Jenkins, replace with githubPush() and add a repository webhook.
        pollSCM('H/2 * * * *')
    }

    environment {
        IMAGE_NAME = 'aceest-fitness'
        REGISTRY_IMAGE = 'docker.io/2025tm93235/aceest-fitness'   // Docker Hub repository
        DOCKERHUB_CREDENTIALS = 'dockerhub-credentials'           // Jenkins credentials id
        APP_IMAGE  = "aceest-fitness:${env.BUILD_NUMBER}"
        TEST_IMAGE = "aceest-fitness:${env.BUILD_NUMBER}-test"
        TEST_CONTAINER  = "aceest-test-${env.BUILD_NUMBER}"
        SMOKE_CONTAINER = "aceest-smoke-${env.BUILD_NUMBER}"
        DEPLOY_TEST_CONTAINER = "aceest-deploy-test-${env.BUILD_NUMBER}"
        // SCM-triggered builds use the parameter defaults (deploy, all, 20%).
        ACTION = "${params.ACTION ?: 'deploy'}"
        DEPLOY_STRATEGY = "${params.DEPLOY_STRATEGY ?: 'all'}"
        CANARY_WEIGHT = "${params.CANARY_WEIGHT ?: '20'}"
        DEPLOYED_FILE = "${env.WORKSPACE}/reports/deployed-strategies.txt"
    }

    stages {
        stage('Checkout') {
            steps {
                deleteDir()                     // start every build from an empty workspace
                checkout scm
                sh 'git log -1 --pretty=format:"Building commit %h by %an: %s%n"'
            }
        }

        stage('Version') {
            steps {
                script {
                    // Single source of truth: __version__ in aceest/__init__.py
                    env.APP_VERSION = sh(
                        returnStdout: true,
                        script: '''sed -n 's/^__version__ = "\\(.*\\)"$/\\1/p' aceest/__init__.py'''
                    ).trim()
                    if (!env.APP_VERSION) {
                        error('Could not read __version__ from aceest/__init__.py')
                    }
                    env.BUILD_TAG_VERSION = "${env.APP_VERSION}-b${env.BUILD_NUMBER}"
                    currentBuild.displayName = "#${env.BUILD_NUMBER} v${env.APP_VERSION}"
                    echo "Application version ${env.APP_VERSION} -> image tags ${env.APP_VERSION}, ${env.BUILD_TAG_VERSION}, latest"
                }
            }
        }

        stage('Build Environment') {
            when { environment name: 'ACTION', value: 'deploy' }
            steps {
                sh '''
                    docker version --format 'Docker client {{.Client.Version}} / server {{.Server.Version}}'
                    docker build --pull --target test -t "$TEST_IMAGE" .
                '''
            }
        }

        stage('Lint & Compile') {
            when { environment name: 'ACTION', value: 'deploy' }
            steps {
                sh '''
                    docker run --rm "$TEST_IMAGE" sh -c \
                        "python -m compileall -q aceest tests deploy_tests *.py && ruff check . && ruff format --check ."
                '''
            }
        }

        stage('Unit Tests') {
            when { environment name: 'ACTION', value: 'deploy' }
            steps {
                sh '''
                    set +e
                    docker run --name "$TEST_CONTAINER" "$TEST_IMAGE" \
                        python -m pytest --junitxml=reports/junit.xml --cov-report=xml:reports/coverage.xml
                    status=$?
                    rm -rf reports
                    docker cp "$TEST_CONTAINER:/app/reports" ./reports
                    docker rm "$TEST_CONTAINER" >/dev/null
                    exit $status
                '''
            }
            post {
                always {
                    junit allowEmptyResults: true, testResults: 'reports/junit.xml'
                    archiveArtifacts artifacts: 'reports/**', allowEmptyArchive: true
                }
            }
        }

        stage('SonarQube Analysis & Quality Gate') {
            when {
                allOf {
                    environment name: 'ACTION', value: 'deploy'
                    expression { return params.RUN_SONAR != false }
                }
            }
            steps {
                script {
                    def scannerHome = tool 'SonarScanner'
                    withSonarQubeEnv('sonarqube') {
                        // -Dsonar.scanner.skipJreProvisioning=true
                        //     Run the scanner on the agent's own Java 17+ instead of downloading
                        //     a JRE from the SonarQube server (that download returned HTTP 500).
                        // -Dsonar.qualitygate.wait=true
                        //     The scanner itself polls SonarQube until the Quality Gate is
                        //     computed and exits non-zero if it is not OK, so no SonarQube ->
                        //     Jenkins webhook and no custom polling code are needed.
                        sh """
                            java -version
                            ${scannerHome}/bin/sonar-scanner \
                                -Dsonar.projectVersion=${env.APP_VERSION} \
                                -Dsonar.scanner.skipJreProvisioning=true \
                                -Dsonar.qualitygate.wait=true \
                                -Dsonar.qualitygate.timeout=300
                        """
                    }
                }
            }
        }

        stage('Build Runtime Image') {
            when { environment name: 'ACTION', value: 'deploy' }
            steps {
                sh 'docker build --target runtime -t "$APP_IMAGE" -t "$IMAGE_NAME:latest" .'
            }
        }

        stage('Smoke Test') {
            when { environment name: 'ACTION', value: 'deploy' }
            steps {
                sh 'bash scripts/smoke_test.sh "$APP_IMAGE" "$SMOKE_CONTAINER"'
            }
        }

        stage('Push to Docker Hub') {
            when { environment name: 'ACTION', value: 'deploy' }
            steps {
                withCredentials([usernamePassword(credentialsId: env.DOCKERHUB_CREDENTIALS,
                                                  usernameVariable: 'DOCKERHUB_USER',
                                                  passwordVariable: 'DOCKERHUB_TOKEN')]) {
                    sh '''
                        echo "$DOCKERHUB_TOKEN" | docker login -u "$DOCKERHUB_USER" --password-stdin
                        for tag in "$APP_VERSION" "$BUILD_TAG_VERSION" latest; do
                            docker tag "$APP_IMAGE" "$REGISTRY_IMAGE:$tag"
                            docker push "$REGISTRY_IMAGE:$tag"
                        done
                        docker logout
                    '''
                }
            }
        }

        stage('Build Artifacts') {
            when { environment name: 'ACTION', value: 'deploy' }
            steps {
                sh '''
                    mkdir -p dist
                    git archive --format=tar.gz --prefix="aceest-fitness-$APP_VERSION/" \
                        -o "dist/aceest-fitness-$APP_VERSION-b$BUILD_NUMBER-src.tar.gz" HEAD
                    digest="$(docker image inspect "$REGISTRY_IMAGE:$BUILD_TAG_VERSION" --format '{{index .RepoDigests 0}}')"
                    size="$(docker image inspect "$APP_IMAGE" --format '{{.Size}}')"
                    cat > dist/build-info.json <<EOF
{
  "application": "aceest-fitness",
  "version": "$APP_VERSION",
  "build_number": $BUILD_NUMBER,
  "git_commit": "$(git rev-parse HEAD)",
  "image": "$REGISTRY_IMAGE:$BUILD_TAG_VERSION",
  "image_tags": ["$APP_VERSION", "$BUILD_TAG_VERSION", "latest"],
  "image_digest": "$digest",
  "image_size_bytes": $size,
  "built_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
}
EOF
                    cat dist/build-info.json
                '''
                archiveArtifacts artifacts: 'dist/**', fingerprint: true
            }
        }

        stage('Deploy to Kubernetes') {
            when { environment name: 'ACTION', value: 'deploy' }
            steps {
                script {
                    env.INGRESS_IP = sh(returnStdout: true, script: 'minikube ip').trim()
                }
                sh '''
                    mkdir -p reports
                    : > "$DEPLOYED_FILE"
                    kubectl config current-context
                    CHANGE_CAUSE="Jenkins build #$BUILD_NUMBER: v$APP_VERSION" \
                        bash k8s/deploy.sh deploy "$DEPLOY_STRATEGY" "$REGISTRY_IMAGE:$BUILD_TAG_VERSION"
                '''
            }
        }

        stage('Post-Deploy Tests') {
            when { environment name: 'ACTION', value: 'deploy' }
            steps {
                sh '''
                    set +e
                    docker run --name "$DEPLOY_TEST_CONTAINER" --network host \
                        -e INGRESS_IP -e DEPLOY_STRATEGY -e CANARY_WEIGHT \
                        -e EXPECTED_VERSION="$APP_VERSION" \
                        "$TEST_IMAGE" python -m pytest deploy_tests -o addopts="" -v \
                        --junitxml=reports/deploy-junit.xml
                    status=$?
                    mkdir -p reports
                    docker cp "$DEPLOY_TEST_CONTAINER:/app/reports/deploy-junit.xml" reports/ || true
                    docker rm "$DEPLOY_TEST_CONTAINER" >/dev/null
                    exit $status
                '''
            }
            post {
                always {
                    junit allowEmptyResults: true, testResults: 'reports/deploy-junit.xml'
                }
            }
        }

        stage('Promote / Rollback') {
            when { not { environment name: 'ACTION', value: 'deploy' } }
            steps {
                sh 'bash k8s/deploy.sh "$ACTION" "$DEPLOY_STRATEGY"'
            }
        }

        stage('Cluster Status') {
            steps {
                sh '''
                    mkdir -p reports
                    bash k8s/deploy.sh status | tee reports/k8s-status.txt
                    kubectl -n aceest rollout history deployment/aceest-rolling | tee -a reports/k8s-status.txt
                '''
                archiveArtifacts artifacts: 'reports/k8s-status.txt, reports/deployed-strategies.txt', allowEmptyArchive: true
            }
        }
    }

    post {
        always {
            sh '''
                docker rm -f "$TEST_CONTAINER" "$SMOKE_CONTAINER" "$DEPLOY_TEST_CONTAINER" >/dev/null 2>&1 || true
                docker rmi "$TEST_IMAGE" "$APP_IMAGE" >/dev/null 2>&1 || true
                docker rmi "$REGISTRY_IMAGE:$BUILD_TAG_VERSION" >/dev/null 2>&1 || true
                docker image prune -f >/dev/null 2>&1 || true
            '''
        }
        success {
            echo "BUILD SUCCESS: action=${env.ACTION}, strategy=${env.DEPLOY_STRATEGY}, version=${env.APP_VERSION} (build #${env.BUILD_NUMBER})."
        }
        failure {
            script {
                // Automatic rollback: revert exactly the strategies this build changed,
                // newest first, so the cluster returns to the last stable version.
                if (env.ACTION == 'deploy' && fileExists('reports/deployed-strategies.txt')) {
                    sh '''
                        tac reports/deployed-strategies.txt | while read -r strategy; do
                            [ -n "$strategy" ] || continue
                            echo "Rolling back $strategy to the last stable version"
                            bash k8s/deploy.sh rollback "$strategy" || true
                        done
                    '''
                }
            }
            echo 'BUILD FAILED: see the stage logs and the JUnit reports above.'
        }
    }
}
