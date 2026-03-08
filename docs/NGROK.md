# Exposing the app with ngrok

Use [ngrok](https://ngrok.com) to expose your local backend and UI on public HTTPS URLs so others can open the login page and chat UI from anywhere.

## 1. Install ngrok

**macOS (Homebrew):**
```bash
brew install ngrok
```

**Or:** Download from [ngrok.com/download](https://ngrok.com/download) and add `ngrok` to your PATH.

## 2. Sign up and authenticate

1. Create a free account at [ngrok.com](https://ngrok.com).
2. Copy your auth token from the [dashboard](https://dashboard.ngrok.com/get-started/your-authtoken).
3. Run:
   ```bash
   ngrok config add-authtoken YOUR_AUTH_TOKEN
   ```

## 3. Start your stack

```bash
cd multi-agent-system
docker compose up -d
```

Wait until the app and agent-ui are healthy (`docker compose ps`).

## 4. Start two ngrok tunnels

Open **two terminals**. In each, run:

**Terminal 1 – backend (login + API):**
```bash
ngrok http 8000
```
Note the **HTTPS** URL ngrok shows (e.g. `https://abc123.ngrok-free.app`). This is your **backend URL**.

**Terminal 2 – UI:**
```bash
ngrok http 3000
```
Note the **HTTPS** URL (e.g. `https://def456.ngrok-free.app`). This is your **UI URL**.

## 5. Configure the app for the public URLs

In the project root, set these in `.env` (or export them) to the ngrok URLs you got:

```bash
# Use your actual ngrok URLs from step 4
AGENT_UI_URL=https://def456.ngrok-free.app
AGENTOS_API_URL=https://abc123.ngrok-free.app
```

Then restart the app and rebuild the UI so the login redirect and CORS use the public URLs, and the UI’s default endpoint is the public backend:

```bash
docker compose build agent-ui
docker compose up -d --force-recreate app agent-ui
```

## 6. Use the public URLs

- **Login page (share this with others):**  
  `https://abc123.ngrok-free.app` or `https://abc123.ngrok-free.app/login`  
  Sign in with **demo** / **password**. You are redirected to the UI with token and endpoint set.

- **Chat UI (optional direct link):**  
  `https://def456.ngrok-free.app`  
  If users open this directly, the backend endpoint is already set (from the rebuild). They can paste a token from the login page if needed.

- **API docs:**  
  `https://abc123.ngrok-free.app/docs`

## Notes

- **Free tier:** ngrok assigns random URLs each time you run `ngrok http ...`. For fixed URLs, use a paid plan or run the tunnels once and keep them open.
- **Keep tunnels running:** Leave both ngrok terminals open while you want the app to be reachable.
- **CORS:** The backend allows the origin from `AGENT_UI_URL`, so the ngrok UI URL must match what you set there.
- **Security:** The demo login (demo/password) is for development. Do not use it in production; protect your ngrok URLs and use proper auth.
