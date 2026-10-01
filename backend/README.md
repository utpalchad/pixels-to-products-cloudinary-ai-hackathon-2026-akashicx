# Pixel Forge Backend

FastAPI backend for Pixel Forge, built for the AkashicX HackIndia submission repository:

`HackIndiaXYZ/pixels-to-products-cloudinary-ai-hackathon-2026-akashicx`

## Architecture

Pixel Forge uses:

- **Gemini 3.1 Flash-Lite** for optional image understanding and structured 3D prompt generation.
- **Pixel Forge local geometry engine** for deterministic relief/lithophane STL and GLB output.
- **three.ws** for optional full image-to-3D reconstruction.
- **No OpenAI dependency.**
- **Cloudinary Upload Widget + delivery URLs** for the browser media layer, with no server-side Cloudinary API secret or SDK dependency.

The HackIndia Cloudinary repository is the project/submission repository. The frontend uses Cloudinary's unsigned Upload Widget. Configure the public cloud name and unsigned upload preset in the frontend environment; the backend never stores a Cloudinary API secret.

```text
Frontend
   |
   +--> /api/v1/analysis/image
   |       +--> Gemini vision when GEMINI_API_KEY is configured
   |       +--> local deterministic prompt fallback
   |
   +--> /api/v1/convert/local
   |       +--> grayscale / smoothing
   |       +--> physical height map
   |       +--> closed mesh generation
   |       +--> STL / GLB / lithophane
   |
   +--> /api/v1/ai3d/generate
           +--> Gemini geometry prompt
           +--> Pixel Forge public source-image URL
           +--> three.ws reconstruction
           +--> /api/v1/jobs/{id}
```

## Run locally

Use Python 3.11+.

```bash
cd backend
python -m venv .venv
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```

Open:

```text
http://localhost:8000/docs
```

## Environment

Local STL/GLB/lithophane generation works without an AI key.

To enable Gemini image analysis:

```env
GEMINI_API_KEY=
GEMINI_MODEL=gemini-3.1-flash-lite
```

For deployed AI 3D mode:

```env
PUBLIC_BASE_URL=https://YOUR-BACKEND.onrender.com
THREEWS_BASE_URL=https://three.ws
THREEWS_DEFAULT_TIER=draft
```

Never commit a populated `.env` file.

## Main endpoints

```http
GET  /health
GET  /providers
POST /api/v1/analysis/image
POST /api/v1/convert/local
POST /api/v1/ai3d/generate
GET  /api/v1/jobs/{job_id}
```

### Image analysis

```bash
curl -X POST http://localhost:8000/api/v1/analysis/image \
  -F "file=@shoe.jpg" \
  -F "provider=auto" \
  -F "description=running shoe"
```

With `provider=auto`, Gemini is used when configured. If the Gemini key is missing or the provider is temporarily unavailable, Pixel Forge falls back to its local prompt builder.

### Local image to STL/GLB

```bash
curl -X POST http://localhost:8000/api/v1/convert/local \
  -F "file=@logo.png" \
  -F "mode=relief" \
  -F "output_format=stl" \
  -F "width_mm=100" \
  -F "depth_mm=8" \
  -F "resolution=128"
```

Modes:

- `relief`
- `lithophane`

Formats:

- `stl`
- `glb`

### AI image to 3D

Upload 1 to 6 views:

```bash
curl -X POST http://localhost:8000/api/v1/ai3d/generate \
  -F "files=@front.jpg" \
  -F "files=@side.jpg" \
  -F "vision_provider=auto" \
  -F "description=preserve the exact proportions" \
  -F "tier=draft"
```

When the frontend uses Cloudinary, its `res.cloudinary.com` delivery URL is passed directly to the backend and then into the 3D pipeline. Raw-file fallback uploads can still be served temporarily from Pixel Forge's own `/files/sources/` route.

## Local conversion engine

```text
Image
  ↓
Resize + normalize
  ↓
Grayscale / height map
  ↓
Pixel intensity → physical height
  ↓
Generate vertices
  ↓
Connect triangle faces
  ↓
Add walls + base
  ↓
Validate closed mesh
  ↓
STL / GLB
```

The local engine creates 2.5D geometry and is best suited to reliefs, lithophanes, logos, embossed art, and height-map-like objects.

## Tests

```bash
cd backend
pytest -q
```

## Render

Build:

```bash
cd backend && pip install -r requirements.txt
```

Start:

```bash
cd backend && uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

Set:

```env
PUBLIC_BASE_URL=https://pixel-forge-api.onrender.com
CORS_ORIGINS=https://forge-pixel-forge.onrender.com
GEMINI_API_KEY=YOUR_KEY
GEMINI_MODEL=gemini-3.1-flash-lite
```

Generated files currently use the Render service filesystem. For a longer-lived production deployment, move generated assets to persistent object storage.
