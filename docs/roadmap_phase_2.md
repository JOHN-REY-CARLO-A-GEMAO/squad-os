# 🛡️ Phase 2: Creative Multimedia (Month 2)

## 🎬 The "Film Crew" Workflow
**Objective:** Coordinate specialized agents to produce multimedia content from a single high-level goal.

### Persona Definitions (`agents/multimedia.py`)
1. **Screenwriter:** Generates scripts and detailed visual prompts for video/image generation.
2. **Storyboarder:** Uses `ImageGenTool` to create keyframes and visual style guides.
3. **Producer:** Manages asset procurement, ensures style consistency, and delegates editing.
4. **Director:** Reviews final cuts, performs QA, and requests retries for failed scenes.

### Workflow Logic: `FilmCrewPackage` (.sqad)
- Uses a conditional DAG:
    - **Step 1:** Screenplay generation.
    - **Step 2:** Parallel generation of Image Assets (Storyboards) and Voiceover (Audio).
    - **Step 3:** Video scene generation based on Storyboards.
    - **Step 4:** Final assembly and scoring.

---

## 🎨 Creative Engine Implementation

### 1. `ImageGenTool` (Python-Native)
- **Library:** `diffusers` + `accelerate`.
- **Strategy:** Local execution on PC (via GPU Offload) or API-based execution for RPi 5.
- **Model Support:** Flux.1-schnell or SDXL Turbo for fast, high-quality local generation.

### 2. `VideoGenTool`
- **Library:** `diffusers` (Stable Video Diffusion) or `Wan2.1` Python wrappers.
- **Capability:**
    - `text_to_video`: Narrative scene generation.
    - `image_to_video`: Animating storyboards created in Step 1.
- **Constraint:** RPi 5 will offload these compute-heavy tasks to the networked GPU machine.

### 3. `NeuralAudioTool`
- **Library:** `Coqui-TTS` for voice and `Audiocraft` for background music.
- **Feature:** "Voice Cloning" from sample files (neural audio gen) as requested in the Guaardvark feature list.

### 4. `AdvancedVideoEditorTool`
- **Library:** `MoviePy` (extending current `VideoProcessingTool`).
- **Features:**
    - Automated cutting and stitching of scenes.
    - Overlaying subtitles and voiceover tracks.
    - Automated transitions based on screenplay markers.

---

## 🛠️ Validation Criteria
1. **Sync Accuracy:** Voiceover and video scene timing must align within 100ms.
2. **Style Consistency:** Images generated for the same "mission" must maintain a shared style embedding.
3. **Offload Stability:** 100% of video generation tasks must be successfully delegated to the GPU node and returned to the RPi 5 coordinator.
