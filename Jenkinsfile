// ACEest Fitness & Gym - Jenkins CI/CD pipeline
//
// Pulls the latest code from GitHub (SCM polling) and runs a clean, fully
// containerised build on the lab VM:
//   Checkout (clean workspace) -> Version -> Build test image -> Lint & compile
//   -> Unit tests in container (JUnit + coverage)
//   -> SonarQube analysis with blocking quality gate
//   -> Build runtime image -> Smoke test -> Push versioned image to Docker Hub
//   -> Build artifacts (build-info.json, source archive, reports)
//
// Everything runs inside Docker, so the agent only needs Git and Docker;
// the host Python version does not matter.

pipeline {
    agent any

    options {
        timestamps()
        timeout(time: 30, unit: 'MINUTES')
        buildDiscarder(logRotator(numToKeepStr: '20'))
        disableConcurrentBuilds()
        skipDefaultCheckout(true)
    }

    parameters {
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
            steps {
                sh '''
                    docker version --format 'Docker client {{.Client.Version}} / server {{.Server.Version}}'
                    docker build --pull --target test -t "$TEST_IMAGE" .
                '''
            }
        }

        stage('Lint & Compile') {
            steps {
                sh '''
                    docker run --rm "$TEST_IMAGE" sh -c \
                        "python -m compileall -q aceest tests deploy_tests *.py && ruff check . && ruff format --check ."
                '''
            }
        }

        stage('Unit Tests') {
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
            when { expression { return params.RUN_SONAR } }
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
            steps {
                sh 'docker build --target runtime -t "$APP_IMAGE" -t "$IMAGE_NAME:latest" .'
            }
        }

        stage('Smoke Test') {
            steps {
                sh 'bash scripts/smoke_test.sh "$APP_IMAGE" "$SMOKE_CONTAINER"'
            }
        }

        stage('Push to Docker Hub') {
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
    }

    post {
        always {
            sh '''
                docker rm -f "$TEST_CONTAINER" "$SMOKE_CONTAINER" >/dev/null 2>&1 || true
                docker rmi "$TEST_IMAGE" "$APP_IMAGE" >/dev/null 2>&1 || true
                docker rmi "$REGISTRY_IMAGE:$BUILD_TAG_VERSION" >/dev/null 2>&1 || true
                docker image prune -f >/dev/null 2>&1 || true
            '''
        }
        success {
            echo "BUILD SUCCESS: ${env.REGISTRY_IMAGE}:${env.BUILD_TAG_VERSION} pushed (build #${env.BUILD_NUMBER})."
        }
        failure {
            echo 'BUILD FAILED: see the stage logs and the JUnit report above.'
        }
    }
}
