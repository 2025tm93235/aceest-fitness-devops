// ACEest Fitness & Gym - Jenkins BUILD pipeline
//
// Secondary validation layer: pulls the latest code from GitHub and performs a
// clean, fully containerised build on the lab VM:
//   Checkout (clean workspace) -> Build test image -> Lint & compile
//   -> Unit tests in container (JUnit + coverage) -> Build runtime image
//   -> [optional SonarQube analysis + quality gate] -> Smoke test -> Image report
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
            defaultValue: false,
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
                        "python -m compileall -q app.py aceest tests && ruff check . && ruff format --check ."
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

        stage('SonarQube Analysis') {
            when { expression { return params.RUN_SONAR } }
            steps {
                script {
                    def scannerHome = tool 'SonarScanner'
                    withSonarQubeEnv('sonarqube') {
                        sh "${scannerHome}/bin/sonar-scanner -Dsonar.projectVersion=${env.BUILD_NUMBER}"
                    }
                }
            }
        }

        stage('Quality Gate') {
            when { expression { return params.RUN_SONAR } }
            steps {
                timeout(time: 5, unit: 'MINUTES') {
                    waitForQualityGate abortPipeline: true
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

        stage('Image Report') {
            steps {
                sh '''
                    docker image inspect "$APP_IMAGE" \
                        --format 'Image {{index .RepoTags 0}} | user={{.Config.User}} | size={{.Size}} bytes'
                    docker image ls "$IMAGE_NAME"
                '''
            }
        }
    }

    post {
        always {
            sh '''
                docker rm -f "$TEST_CONTAINER" "$SMOKE_CONTAINER" >/dev/null 2>&1 || true
                docker rmi "$TEST_IMAGE" "$APP_IMAGE" >/dev/null 2>&1 || true
                docker image prune -f >/dev/null 2>&1 || true
            '''
        }
        success {
            echo "BUILD SUCCESS: ${env.IMAGE_NAME}:latest is ready (build #${env.BUILD_NUMBER})."
        }
        failure {
            echo 'BUILD FAILED: see the stage logs and the JUnit report above.'
        }
    }
}
