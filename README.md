# Pixel Forge

> **Turn pixels into form.**

Pixel Forge is an image-to-3D creation platform built by **AkashicX** for the **Pixels to Products — Cloudinary AI Hackathon 2026**. It transforms ordinary JPG, PNG, and WebP images into usable **STL**, **GLB**, and **3D-printable lithophane** outputs through a spatial web interface.

## What it does

- Upload images through the **Cloudinary Upload Widget**
- Use Cloudinary delivery URLs as the media layer for downstream processing
- Analyze reference images with **Gemini 3.1 Flash-Lite**
- Generate deterministic reliefs and lithophanes with our custom Python geometry engine
- Export **STL** and **GLB**
- Use 1–6 views for optional AI-assisted full 3D reconstruction
- Preview and tune geometry through a Three.js / React Three Fiber interface

## Architecture

```text
User image
   |
   v
Cloudinary Upload Widget
   |
   +--> Cloudinary delivery URL
   |
   v
Gemini image analysis
   |
   +--> structured 3D prompt / geometry hints
   |
   v
Pixel Forge Router
   |
   +-----------------------------+
   |                             |
   v                             v
Local Mesh Engine          AI 3D Reconstruction
   |                             |
   +--> relief                    +--> textured GLB
   +--> lithophane
   +--> STL / GLB
   |
   v
Three.js Preview + Export
```

Cloudinary is used as a real browser media layer. The frontend uses an **unsigned Upload Widget preset**, so no Cloudinary API secret is exposed to the browser or required by the FastAPI backend.

## Tech stack

### Frontend
- Next.js 14
- React
- TypeScript
- Three.js
- React Three Fiber
- Drei
- GSAP
- Cloudinary Upload Widget

### Backend
- FastAPI
- NumPy
- Pillow
- trimesh
- Gemini API
- optional three.ws full 3D route

## Local geometry engine

For relief and lithophane generation, Pixel Forge owns the geometry pipeline:

```text
Image
  -> resize / normalize
  -> grayscale
  -> physical height map
  -> vertices
  -> triangle faces
  -> walls + base
  -> closed mesh validation
  -> STL / GLB
```

A simplified relief mapping is:

```text
height = base_thickness + normalized_brightness * depth
```

Lithophane mode reverses luminance so darker regions become thicker.

## Run the frontend

```bash
npm install
cp .env.example .env.local
npm run dev
```

Frontend environment:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_CLOUDINARY_CLOUD_NAME=your_cloud_name
NEXT_PUBLIC_CLOUDINARY_UPLOAD_PRESET=your_unsigned_upload_preset
```

## Run the backend

```bash
cd backend
python -m venv .venv
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```

Backend environment:

```env
PUBLIC_BASE_URL=http://localhost:8000
CORS_ORIGINS=http://localhost:3000
GEMINI_API_KEY=
GEMINI_MODEL=gemini-3.1-flash-lite
THREEWS_BASE_URL=https://three.ws
THREEWS_DEFAULT_TIER=draft
```

The deterministic STL/GLB/lithophane engine works without a Gemini key. Gemini is used for richer image understanding and prompt generation when configured.

## Main API routes

```text
GET  /health
GET  /providers
POST /api/v1/analysis/image
POST /api/v1/convert/local
POST /api/v1/ai3d/generate
GET  /api/v1/jobs/{job_id}
```

Interactive FastAPI documentation is available at `/docs` when the backend is running.

## Deployment

The frontend and backend can be deployed as separate Render web services.

Frontend:

```text
Build: npm install && npm run build
Start: npm start
```

Backend:

```text
Build: cd backend && pip install -r requirements.txt
Start: cd backend && uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

Set the production frontend API URL to the deployed backend URL and set backend CORS to the frontend origin.

## Repository

This fork is based on the official team repository:

`HackIndiaXYZ/pixels-to-products-cloudinary-ai-hackathon-2026-akashicx`

Team: **AkashicX**

## License

MIT
