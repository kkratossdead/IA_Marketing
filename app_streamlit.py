import streamlit as st
import google.generativeai as genai
from PIL import Image
from io import BytesIO
import base64
import os
from datetime import datetime

# ------------------------------------------------------------------
# Early session_state initialization to avoid KeyError on first load
# ------------------------------------------------------------------
for _key, _default in {
    "enhanced_prompt": "",
    "results": [],
    "library": [],
    "last_prompt": "",
}.items():
    if _key not in st.session_state:
        st.session_state[_key] = _default

# -----------------------------
# Page config & base styles
# -----------------------------
st.set_page_config(
    page_title="Auto Creative Lab – Gemini",
    page_icon="🚗",
    layout="wide"
)

PRIMARY = "#0E7AFE"  # brand accent (you can customize)
ACCENT = "#101828"   # dark text
MUTED = "#667085"    # muted text
BORDER = "#EAECF0"   # borders

st.markdown(
    f"""
    <style>
      .app-header {{
        display:flex;align-items:center;gap:12px;margin-bottom:10px
      }}
      .badge {{
        display:inline-flex;align-items:center;gap:6px;padding:6px 10px;border:1px solid {BORDER};
        border-radius:999px;font-size:12px;color:{MUTED};background:rgba(16,24,40,0.02);
      }}
      .card {{
        border:1px solid {BORDER}; border-radius:16px; padding:16px; background:white;
      }}
    .ghost {{ background:linear-gradient(180deg, rgba(14,122,254,0.06) 0%, rgba(14,122,254,0.02) 100%) }}
      .pill {{
        padding:6px 10px;border-radius:999px;border:1px dashed {BORDER};font-size:12px;color:{MUTED};
      }}
      .tiny {{font-size:12px;color:{MUTED}}}
      .btn-primary button {{
        background:{PRIMARY} !important;border:1px solid {PRIMARY} !important;color:white !important;
      }}
      .btn-outline button {{
        background:white !important;border:1px solid {BORDER} !important;color:{ACCENT} !important;
      }}
      .result-img {{ border-radius:14px; border:1px solid {BORDER}; }}
      hr {{ border: none; border-top: 1px solid {BORDER}; margin: 12px 0 20px; }}
    </style>
    """,
    unsafe_allow_html=True,
)

# -----------------------------
# Sidebar (Settings)
# -----------------------------
st.sidebar.markdown("## ⚙️ Settings")
API_KEY = st.sidebar.text_input("Gemini API Key", type="password")
# Exemple d'initialisation directe (à ne pas faire en production) :
# API_KEY = "votre_cle_api_gemini_ici"
#
# Pour initialiser la clé API via un fichier .env (recommandé) :
# Ajouter la ligne suivante dans un fichier .env à la racine du projet :
# GEMINI_API_KEY=votre_cle_api_gemini_ici


if not API_KEY:
    API_KEY = os.getenv("GEMINI_API_KEY")
MODEL_NAME = st.sidebar.selectbox(
    "Model",
    [
        "gemini-2.5-flash-image-preview",
    ],
    index=0,
)

ratio = st.sidebar.selectbox(
    "Aspect Ratio",
    ["1:1", "4:5", "9:16", "16:9", "3:4"],
    help="Used to guide the image composition."
)

seed = st.sidebar.number_input("Seed (optional)", min_value=0, value=0)

st.sidebar.markdown("---")
st.sidebar.markdown("### Output")
show_captions = st.sidebar.toggle("Show captions", value=True)

# -----------------------------
# Header
# -----------------------------
colA, colB = st.columns([0.65,0.35])
with colA:
    st.markdown(
        """
        <div class="app-header">
          <h1 style="margin:0">Image Replacement & Marketing Generator</h1>
        </div>
        <p style="margin-top:-6px;color:#667085">Design mockup for an automotive brand: swap/augment visuals, craft campaign-ready images, and export in a click.</p>
        """,
        unsafe_allow_html=True,
    )
with colB:
    st.markdown(
        """
        <div class="card ghost">
          <b>Tips</b>
          <ul style="margin:8px 0 0 16px;color:#475467">
            <li>Add 0–3 reference images in the order of priority.</li>
            <li>Keep prompts specific (model, trim, color, scene, mood).</li>
            <li>Use <span class="pill">brand colors</span> and <span class="pill">CTA overlays</span> in your prompt for marketing shots.</li>
          </ul>
        </div>
        """,
        unsafe_allow_html=True,
    )

# -----------------------------
# Prompt Builder
# -----------------------------
with st.container():
    st.markdown("### ✍️ Prompt")
    left, right = st.columns([0.6,0.4])
    with left:
        # Inject replacement prompt (avant création du widget) si demandé
        if "temp_prompt_replacement" in st.session_state:
            st.session_state["prompt_input"] = st.session_state["temp_prompt_replacement"]
            del st.session_state["temp_prompt_replacement"]
            st.session_state["show_replace_success"] = True

        prompt = st.text_area(
            "Describe the target image",
            key="prompt_input",  # la valeur initiale provient de session_state si existante
            placeholder=(
                "e.g. Replace the car with a white Volkswagen T-Roc, black roof, glossy black wheels, "
                "sport grille, LED headlights, parked on a cliff, ocean and pine trees in the background; "
                "cinematic light, editorial quality, brand hero shot."
            ),
            height=140,
        )
        # Message de confirmation après rerun
        if st.session_state.get("show_replace_success"):
            st.success("Base prompt replaced.")
            del st.session_state["show_replace_success"]
    with right:
        preset = st.selectbox(
            "Presets",
            [
                "— None",
                "Studio – glossy floor, softbox reflection, brand backdrop",
                "Lifestyle – sunset coast road, motion blur, lens flare",
                "Social Ad – top-down, product-first, bold CTA zone",
                "Configurator – clean side profile, neutral light, shadow",
            ],
            index=0,
        )
        if preset and preset != "— None":
            add_on = {
                "Studio – glossy floor, softbox reflection, brand backdrop": "studio lighting, glossy floor reflections, seamless backdrop with subtle logo pattern",
                "Lifestyle – sunset coast road, motion blur, lens flare": "golden hour, coastal road, slight motion blur, natural lens flare, lifestyle feel",
                "Social Ad – top-down, product-first, bold CTA zone": "flat-lay/top-down camera, high contrast, clear negative space for CTA overlay",
                "Configurator – clean side profile, neutral light, shadow": "orthographic side view, neutral lighting, realistic soft shadow on ground",
            }[preset]
            prompt = (prompt + ("\n\n" if prompt else "") + add_on).strip()
            st.info("Preset applied to prompt.")

# -----------------------------
# Prompt Enhancer Functions (définies avant utilisation)
# -----------------------------
@st.cache_resource(show_spinner=False)
def _text_model(api_key: str):
    genai.configure(api_key=api_key)
    return genai.GenerativeModel("gemini-2.0-flash")

def enhance_prompt(base_prompt: str, aspect_ratio: str, preset_label: str, uploaded_images=None) -> str:
    """
    Appelle un modèle texte pour booster le prompt utilisateur avec une approche de Prompt Enhancer AI.
    """
    system_hint = (
        "Act as a Prompt Enhancer AI that takes user-input prompts and transforms them into more engaging, "
        "detailed, and thought-provoking image generation prompts. Describe the process you follow to enhance a prompt, "
        "the types of improvements you make, and share an example of how you'd turn a simple, one-sentence prompt into an "
        "enriched, multi-layered description that encourages deeper visual thinking and more insightful image generation.\n\n"
        
        "Your enhancement process follows these steps:\n"
        "1. ANALYZE the user's basic request to identify core visual elements and intent\n"
        "2. EXPAND with rich descriptive details (lighting, composition, mood, materials, textures)\n"
        "3. ENHANCE with professional photography/cinematography techniques\n"
        "4. LAYER multiple dimensions of visual storytelling (emotional, technical, aesthetic)\n"
        "5. STRUCTURE for maximum AI image generation effectiveness\n\n"
        
        "Transform simple prompts into multi-layered, comprehensive descriptions that include:\n"
        "- Precise technical specifications (camera angles, lighting setup, focal length, depth of field)\n"
        "- Emotional and atmospheric elements (mood, feeling, brand personality, narrative)\n"
        "- Visual composition rules (rule of thirds, negative space, leading lines, symmetry)\n"
        "- Material and texture details (paint reflections, surface properties, environmental interactions)\n"
        "- Professional quality indicators (editorial style, commercial photography standards)\n"
        "- Sensory elements that translate to visual impact (temperature, movement, energy)\n\n"
        
        "Example transformation:\n"
        "Simple prompt: 'White car on road'\n"
        "Enhanced prompt: 'Pristine white luxury sedan positioned dynamically on a winding coastal highway, "
        "captured with a 85mm lens at f/2.8 creating shallow depth of field, golden hour lighting casting warm "
        "reflections across the polished paint surface, dramatic ocean vista stretching to the horizon, "
        "composition following rule of thirds with negative space for brand messaging, editorial automotive "
        "photography style with crisp details and natural shadows, conveying freedom and aspiration.'\n\n"
        
        "Return ONLY the enhanced prompt - no explanations, no commentary, just the improved prompt ready for image generation."
    )
    
    constraints_and_context = (
        f"Target aspect ratio: {aspect_ratio}\n"
        "Requirements: Crisp details, natural reflections on paint, realistic shadows, "
        "no text baked into the image, avoid watermarks, editorial/commercial quality.\n"
    )
    
    if preset_label and preset_label != "— None":
        constraints_and_context += f"Style preset to incorporate: {preset_label}\n"
    
    if uploaded_images:
        img_count = len(uploaded_images)
        constraints_and_context += f"Reference images provided ({img_count} images): Use their style, composition, lighting, and mood as inspiration for the enhanced prompt.\n"
    
    user_input = f"Original user prompt to enhance: \"{base_prompt}\"\n\n{constraints_and_context}"

    try:
        model_txt = _text_model(API_KEY)
        resp = model_txt.generate_content([system_hint, user_input])
        return resp.text.strip()
    except Exception:
        return base_prompt  # fallback

# Bouton Prompt Enhancer placé sous la zone de prompt
enhance_btn = st.button("✨ Prompt Enhancer", help="Transform your  basic prompt into a detailed, professional image generation prompt")

# (State key 'enhanced_prompt' already initialized above)

if enhance_btn:
    if not API_KEY:
        st.error("Please enter your Gemini API key in the sidebar before enhancing.")
    elif not st.session_state.get("prompt_input"):
        st.warning("Write a base prompt first.")
    else:
        with st.spinner("Enhancing your prompt with AI..."):
            improved = enhance_prompt(
                base_prompt=st.session_state["prompt_input"],
                aspect_ratio=ratio,
                preset_label=preset,
                uploaded_images=None
            )
        st.session_state["enhanced_prompt"] = improved

# Affichage du prompt amélioré avec hauteur adaptative (utilise .get pour robustesse)
if st.session_state.get("enhanced_prompt"):
    st.markdown("##### ✅ Enhanced Prompt")
    # Calcul de la hauteur basée sur la longueur du texte
    text_length = len(st.session_state["enhanced_prompt"])
    height = max(140, min(400, text_length // 3))  # Hauteur adaptative entre 140 et 400px
    
    st.text_area(
        "Enhanced prompt (ready to use):",
        value=st.session_state["enhanced_prompt"],
        height=height,
        disabled=True,
        key="enhanced_display"
    )
    
    rep_col1, rep_col2 = st.columns([0.25, 0.75])
    with rep_col1:
        if st.button("↔️ Replace base prompt"):
            # Utiliser st.experimental_set_query_params pour forcer le rechargement avec la nouvelle valeur
            if "enhanced_prompt" in st.session_state and st.session_state["enhanced_prompt"]:
                # Stocker temporairement la valeur enhanced dans une autre clé
                st.session_state["temp_prompt_replacement"] = st.session_state["enhanced_prompt"]
                st.success("Base prompt will be replaced on next refresh.")
                st.rerun()

# -----------------------------
# Upload Zone (déplacée avant le Prompt Enhancer)
# -----------------------------
st.markdown("### 🖼️ Reference Images (optional)")
uploaded_images = st.file_uploader(
    "Drop up to 3 images (order = priority)",
    type=["jpg", "jpeg", "png"],
    accept_multiple_files=True,
    key="reference_images_uploader"
)

if uploaded_images:
    grid_cols = st.columns(min(3, len(uploaded_images)))
    for i, file in enumerate(uploaded_images[:3]):
        with grid_cols[i % len(grid_cols)]:
            try:
                img = Image.open(file)
                st.image(
                    img, 
                    caption=f"#{i+1} – {file.name}",   # numérotation + nom
                    width=180                        # taille fixe plus petite
                )
            except Exception as e:
                st.warning(f"Could not preview {file.name}: {e}")

# -----------------------------
# Call Gemini
# -----------------------------
@st.cache_resource(show_spinner=False)
def _configure(api_key: str, model_name: str):
    genai.configure(api_key=api_key)
    return genai.GenerativeModel(model_name)

run_col1, run_col2 = st.columns([0.5,0.5])
with run_col1:
    gen_btn = st.button("🚀 Generate", type="primary")
with run_col2:
    clear_btn = st.button("🧹 Clear Results", type="secondary")

if clear_btn:
    st.session_state["results"] = []
    st.session_state["last_prompt"] = ""

if gen_btn:
    if not API_KEY:
        st.error("Please enter your Gemini API key in the sidebar.")
    elif not prompt:
        st.warning("Write a prompt first.")
    else:
        try:
            model = _configure(API_KEY, MODEL_NAME)

            # Compose the input for Gemini: prompt + images (if any) + guidance
            guide = (
                f"Aspect ratio {ratio}. Return only images, no text. "
                f"If multiple variations requested, produce 1 image."
            )
            seed_clause = f" Seed: {seed}." if seed else ""
            full_prompt = f"{prompt}\n\n{guide}{seed_clause}".strip()

            vision_inputs = [full_prompt]
            if uploaded_images:
                for file in uploaded_images[:3]:
                    try:
                        vision_inputs.append(Image.open(file))
                    except Exception as e:
                        st.warning(f"Could not open image: {file.name} ({e})")

            with st.spinner("Generating visuals…"):
                resp = model.generate_content(vision_inputs)

            results = []
            try:
                parts = resp.candidates[0].content.parts
            except Exception:
                parts = []

            for part in parts:
                data = getattr(part, "inline_data", None)
                if data and getattr(data, "mime_type", "").startswith("image"):
                    try:
                        raw = data.data  # bytes
                        img = Image.open(BytesIO(raw))
                        results.append((img, raw))
                    except Exception as e:
                        st.warning(f"Returned image couldn't be decoded: {e}")

            if not results:
                st.warning("No image returned. Try refining the prompt or adding a reference image.")
            else:
                st.session_state["results"] = results
                st.session_state["last_prompt"] = full_prompt
        except Exception as e:
            st.error(f"Error: {e}")

# -----------------------------
# Results Grid
# -----------------------------
if "results" in st.session_state and st.session_state["results"]:
    st.markdown("### ✅ Results")
    cols = st.columns(4)
    for i, (img, raw) in enumerate(st.session_state["results"]):
        with cols[i % 4]:
            st.image(img, width='stretch', output_format="PNG")
            if show_captions:
                st.caption(f"Result {i+1}")
            st.download_button(
                label=f"Download #{i+1}",
                data=raw,
                file_name=f"auto_creative_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{i+1}.png",
                mime="image/png",
                use_container_width=True,
            )


# -----------------------------
# Library of past generations
# -----------------------------
if "library" not in st.session_state:
    st.session_state["library"] = []

# Quand on génère, sauvegarde dans la bibliothèque
if gen_btn and st.session_state.get("results"):
    st.session_state["library"].append({
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "prompt": st.session_state["last_prompt"],
        "results": st.session_state["results"]
    })

if st.session_state["library"]:
    st.markdown("### 📚 Library")
    for idx, entry in enumerate(reversed(st.session_state["library"])):
        with st.expander(f"Generation {len(st.session_state['library']) - idx} – {entry['timestamp']}"):
            st.markdown(f"**Prompt used:**\n\n```\n{entry['prompt']}\n```")
            cols = st.columns(4)
            for i, (img, raw) in enumerate(entry["results"]):
                with cols[i % 4]:
                    st.image(img, width='stretch', output_format="PNG")
                    st.download_button(
                        label=f"Download #{i+1}",
                        data=raw,
                        file_name=f"auto_creative_{entry['timestamp'].replace(':','-')}_{i+1}.png",
                        mime="image/png",
                        use_container_width=True,
                    )


# -----------------------------
# Footer / Debug
# -----------------------------
with st.expander("🔍 Debug / Prompt Preview"):
    st.code(st.session_state.get("last_prompt", ""), language="md")

st.markdown("<hr>", unsafe_allow_html=True)
st.markdown(
    "<div class='tiny'>Built for automotive marketing teams · Streamlit UI mock · Gemini backend.\n" \
    "Use responsibly and verify license compliance for any brand assets.</div>",
    unsafe_allow_html=True,
)
