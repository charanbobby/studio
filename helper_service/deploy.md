# Deploying the Helper service to the Hetzner VPS

Prerequisites: SSH access to the studio.sshub.dev VPS as user `sri`. The studio.sshub.dev nginx + Sri Studio app are already deployed (see studio repo's deploy notes).

```bash
# 1. From local repo, build and save the image as a tarball
cd "D:/Python Applications/Sri Studio Helper"
docker build -f helper_service/Dockerfile -t sri-studio-helper:latest .
docker save sri-studio-helper:latest | gzip > /tmp/helper-image.tar.gz

# 2. Copy artifacts to VPS
scp /tmp/helper-image.tar.gz sri@studio.sshub.dev:/tmp/
scp helper_service/docker-compose.yml sri@studio.sshub.dev:/srv/helper/
scp helper_service/.env.example       sri@studio.sshub.dev:/srv/helper/

# 3. SSH in and finish setup
ssh sri@studio.sshub.dev
sudo mkdir -p /srv/helper && sudo chown sri /srv/helper
cd /srv/helper
docker load < /tmp/helper-image.tar.gz
cp .env.example .env
# Edit .env: set ELEVENLABS_API_KEY (from 1Password) and HELPER_AUTH_KEY (random hex; save in 1Password)
nano .env
docker compose up -d
docker compose logs --tail=20

# 4. Wire nginx
sudo cat helper_service/nginx-helper.conf  # paste into /etc/nginx/sites-available/studio.sshub.dev inside the existing server block
sudo nginx -t && sudo systemctl reload nginx

# 5. Smoke test from VPS
curl -H "X-Helper-Key: $(grep HELPER_AUTH_KEY /srv/helper/.env | cut -d= -f2)" \
  http://127.0.0.1:8001/helper/health

# 6. Smoke test from external
curl -H "X-Helper-Key: ..." https://studio.sshub.dev/helper/health
```
