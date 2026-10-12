# Evidence screenshots

Save the screenshots as PNG files in this folder, using the file names below,
then commit them (`docs: add pipeline evidence screenshots`).

| # | File name | What to capture |
|---|---|---|
| 1 | `01-github-repo.png` | Repository home page (public, README rendered, CI badge green) |
| 2 | `02-github-branches-prs.png` | **Pull requests → Closed** list showing the merged feature/ci/docs PRs |
| 3 | `03-github-commits.png` | Commit history of `main` (Conventional Commit messages) |
| 4 | `04-actions-runs.png` | **Actions** tab: list of green workflow runs for push and pull_request events |
| 5 | `05-actions-jobs.png` | One run's summary: *Build & Lint → Docker Image Assembly → Automated Testing* all green |
| 6 | `06-actions-pytest-log.png` | "Run pytest inside the container" step log showing tests passed and coverage ≥ 90 % |
| 7 | `07-jenkins-job-config.png` | Jenkins job configuration: Pipeline script from SCM, repo URL, `*/main`, `Jenkinsfile` |
| 8 | `08-jenkins-stage-view.png` | Job page **Stage View** with all stages green |
| 9 | `09-jenkins-console.png` | Console output tail showing the smoke test and `Finished: SUCCESS` |
| 10 | `10-jenkins-tests.png` | Build **Test Result** page (all tests passed) |
| 11 | `11-jenkins-scm-trigger.png` | Build cause *Started by an SCM change* and/or **Polling Log** |
| 12 | `12-docker-image.png` | Terminal output of `docker image ls aceest-fitness` and `docker inspect --format '{{.Config.User}}' aceest-fitness:latest` |
| 13 | `13-app-dashboard.png` | Running app: dashboard with clients |
| 14 | `14-app-client-page.png` | Running app: client page (summary, progress bars, generated program) |
| 15 | `15-sonarqube.png` | *(optional)* SonarQube project overview with Quality Gate *Passed* |
