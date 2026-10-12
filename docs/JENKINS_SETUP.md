# Jenkins BUILD setup on the lab VM (Rocky Linux 9)

This guide configures the existing Jenkins on the lab VM to build
`aceest-fitness-devops` from GitHub with the repository's `Jenkinsfile`.

Assumed (already installed on the VM): Jenkins, Docker, Git, SonarQube, and
internet access. Commands are run as a user with `sudo`.

> Replace `2025tm93235` with your GitHub user name throughout.

---

## 1. Verify the prerequisites

```bash
cat /etc/rocky-release                 # Rocky Linux release 9.5 (Blue Onyx)
systemctl is-active jenkins docker     # both should print: active
java -version                          # Java 17 or 21 (required by Jenkins)
git --version
docker version                         # must show "Server: Docker Engine - Community"
```

If `docker version` reports **Podman** (the `podman-docker` shim), install Docker
Engine before continuing. The pipeline expects the Docker daemon (BuildKit
`--target` builds, `docker cp`, health checks):

```bash
sudo dnf -y install dnf-plugins-core
sudo dnf config-manager --add-repo https://download.docker.com/linux/rhel/docker-ce.repo
sudo dnf -y install docker-ce docker-ce-cli containerd.io docker-buildx-plugin
sudo systemctl enable --now docker
```

## 2. Let Jenkins use Docker

The pipeline runs `docker` as the `jenkins` user.

```bash
sudo usermod -aG docker jenkins
sudo systemctl restart jenkins
sudo -u jenkins docker ps              # must NOT print "permission denied"
sudo -u jenkins docker run --rm hello-world
```

## 3. Open the Jenkins UI

Browse to `http://<VM-IP>:8080`. If the page does not load from your laptop,
open the port in the VM firewall:

```bash
sudo firewall-cmd --permanent --add-port=8080/tcp
sudo firewall-cmd --reload
```

## 4. Check the required plugins

**Manage Jenkins → Plugins → Installed plugins.** Install any that are
missing from **Available plugins**, then restart Jenkins:

| Plugin | Used for |
|---|---|
| Pipeline | Declarative `Jenkinsfile` |
| Git | `checkout scm` from GitHub |
| JUnit | Publishing `reports/junit.xml` |
| Timestamper | `timestamps()` option |
| Pipeline: Stage View | Stage view for evidence screenshots |
| SonarQube Scanner | *Only for the optional SonarQube stage* |

(All except SonarQube Scanner are part of the "suggested plugins" set.)

## 5. Create the pipeline job

1. **Dashboard → New Item**
2. Name: `aceest-fitness-devops`, type **Pipeline**, click **OK**.
3. **General**: tick *GitHub project* and enter
   `https://github.com/2025tm93235/aceest-fitness-devops/` (optional, adds a link).
4. **Pipeline** section:
   - Definition: **Pipeline script from SCM**
   - SCM: **Git**
   - Repository URL: `https://github.com/2025tm93235/aceest-fitness-devops.git`
   - Credentials: *none* (the repository is public)
   - Branch Specifier: `*/main`
   - Script Path: `Jenkinsfile`
   - Tick **Lightweight checkout**
5. **Save**.

You do not need to configure **Build Triggers** here: the `Jenkinsfile`
declares `pollSCM('H/2 * * * *')`, and so do the `RUN_SONAR` parameter and the
other options.

## 6. First build (registers the trigger)

1. Click **Build Now**. The first run reads the `Jenkinsfile` and registers
   the polling trigger and the `RUN_SONAR` parameter. After that the button
   reads **Build with Parameters**.
2. Open the build → **Console Output**. The stages should be:
   `Checkout → Build Environment → Lint & Compile → Unit Tests →
   Build Runtime Image → Smoke Test → Image Report`, ending in
   `Finished: SUCCESS`.
3. The job page now shows **Stage View** and a **Test Result Trend**, and
   the build page has **Test Result** (JUnit) and **Build Artifacts**
   (`reports/junit.xml`, `reports/coverage.xml`).
4. Open **Configure** again: under *Build Triggers*, **Poll SCM** is now
   ticked with `H/2 * * * *` (set by the Jenkinsfile).

## 7. Verify the automatic trigger

1. Push any commit to `main` (for example, merge a pull request).
2. Within about 2 minutes, a new build starts on its own. **Polling Log** on the
   job page shows `Changes found`, and the build's cause is
   *Started by an SCM change*.

### Optional: GitHub webhook instead of polling

Use this only if GitHub can reach the VM over the internet (public IP or a
tunnel):

1. Install the **GitHub** plugin (usually already installed).
2. In the `Jenkinsfile`, replace `pollSCM('H/2 * * * *')` with `githubPush()`.
3. GitHub repository → **Settings → Webhooks → Add webhook**:
   Payload URL `http://<public-host>:8080/github-webhook/`,
   content type `application/json`, event *Just the push event*.

## 8. Optional: SonarQube analysis and Quality Gate

The pipeline has a `RUN_SONAR` parameter (default off). To turn it on:

1. **SonarQube** (`http://<VM-IP>:9000`): **My Account → Security → Generate
   Token** (type *Global Analysis Token*). Copy the token.
2. **Jenkins → Manage Jenkins → Credentials → System → Global → Add
   Credentials**: kind *Secret text*, Secret = token, ID `sonarqube-token`.
3. **Manage Jenkins → System → SonarQube servers**: tick *Environment
   variables*, **Add SonarQube**: Name `sonarqube` (must match the Jenkinsfile),
   Server URL `http://localhost:9000` (or the SonarQube host), token
   `sonarqube-token`. Save.
4. **Manage Jenkins → Tools → SonarQube Scanner installations → Add**:
   Name `SonarScanner` (must match), tick *Install automatically*. Save.
5. **SonarQube → Administration → Configuration → Webhooks → Create**:
   Name `jenkins`, URL `http://<jenkins-host>:8080/sonarqube-webhook/`.
   If SonarQube itself runs in a container, use the VM IP rather than
   `localhost`. The Quality Gate stage waits for this callback.
6. Run **Build with Parameters** with `RUN_SONAR` ticked. The project
   `aceest-fitness-devops` appears in SonarQube with coverage from
   `reports/coverage.xml`.

## 9. Run the application on the VM (for demo screenshots)

```bash
docker run -d --name aceest -p 5000:5000 \
  -e ACEEST_ADMIN_PASSWORD='choose-a-password' \
  -e ACEEST_SECRET_KEY="$(openssl rand -hex 32)" \
  -v aceest-data:/app/instance \
  aceest-fitness:latest            # image produced by the last Jenkins build
sudo firewall-cmd --permanent --add-port=5000/tcp && sudo firewall-cmd --reload
```

Open `http://<VM-IP>:5000` and log in as `admin`. Stop it with
`docker rm -f aceest`. The data stays in the `aceest-data` volume.

## 10. Troubleshooting

| Symptom | Fix |
|---|---|
| `permission denied ... /var/run/docker.sock` | Step 2: add `jenkins` to the `docker` group and **restart Jenkins** |
| `No such DSL method 'timestamps'` | Install the **Timestamper** plugin |
| `No such DSL method 'junit'` | Install the **JUnit** plugin |
| Builds never start automatically | Run one build manually first (step 6); check **Polling Log** |
| `Error: could not find tool 'SonarScanner'` | Step 8.4 name must be exactly `SonarScanner` |
| Quality Gate stage times out | SonarQube webhook (step 8.5) is missing or points to an unreachable URL |
| Base image pull fails | VM needs outbound HTTPS to Docker Hub (`registry-1.docker.io`) |
| Disk fills up over time | `docker system prune -f` (the pipeline already removes its per-build images) |

## 11. Evidence to capture

See [screenshots/README.md](screenshots/README.md) for the checklist of
screenshots to add to the repository.
