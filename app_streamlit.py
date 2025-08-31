import streamlit as st
import google.generativeai as genai
from PIL import Image
from io import BytesIO
import base64
import os
from datetime import datetime

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
        prompt = st.text_area(
            "Describe the target image",
            key="prompt_input",  # important pour manipuler via session_state
            placeholder=(
                "e.g. Replace the car with a white Volkswagen T-Roc, black roof, glossy black wheels, "
                "sport grille, LED headlights, parked on a cliff, ocean and pine trees in the background; "
                "cinematic light, editorial quality, brand hero shot."
            ),
            height=140,
        )
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

# # -----------------------------
# # Prompt Enhancer (Gemini text)
# # -----------------------------
# @st.cache_resource(show_spinner=False)
# def _text_model(api_key: str):
#     genai.configure(api_key=api_key)
#     return genai.GenerativeModel("gemini-2.0-flash")

# def enhance_prompt(base_prompt: str, aspect_ratio: str, preset_label: str) -> str:
#     """
#     Appelle un modèle texte pour booster le prompt utilisateur.
#     """
#     system_hint = (
#         "You are an expert creative director for automotive marketing shots. "
#         "Rewrite and optimize the user's prompt for image generation. "
#         "Keep it concise but richly descriptive (camera, lighting, scene, materials, reflections). "
#         "Enforce brand-friendly composition with clean negative space for CTA if relevant. "
#         "Return ONLY the improved prompt, no commentary."
#     )
#     constraints = (
#         f"Aspect ratio: {aspect_ratio}. "
#         "If applicable: crisp details, natural reflections on paint, realistic shadows, "
#         "no text baked into the image, avoid watermarks, editorial quality."
#     )
#     if preset_label and preset_label != "— None":
#         constraints += f" Style preset: {preset_label}."
#     user = f"Original prompt: {base_prompt}"

#     model_txt = _text_model(API_KEY)
#     resp = model_txt.generate_content([system_hint, constraints, user])
#     try:
#         return resp.text.strip()
#     except Exception:
#         return base_prompt  # fallback

# enh_col1, enh_col2, enh_col3 = st.columns([0.25, 0.25, 0.5])
# with enh_col1:
#     enhance_btn = st.button("✨ Prompt Enhancer", help="Improve the prompt for best image results")

# # Espace pour stocker et afficher la version améliorée
# if "enhanced_prompt" not in st.session_state:
#     st.session_state["enhanced_prompt"] = ""

# if enhance_btn:
#     if not API_KEY:
#         st.error("Please enter your Gemini API key in the sidebar before enhancing.")
#     elif not st.session_state.get("prompt_input"):
#         st.warning("Write a base prompt first.")
#     else:
#         with st.spinner("Enhancing prompt…"):
#             improved = enhance_prompt(
#                 base_prompt=st.session_state["prompt_input"],
#                 aspect_ratio=ratio,
#                 preset_label=preset
#             )
#         st.session_state["enhanced_prompt"] = improved

# # Affichage du prompt amélioré
# if st.session_state["enhanced_prompt"]:
#     st.markdown("##### ✅ Enhanced Prompt")
#     st.code(st.session_state["enhanced_prompt"], language="md")
#     rep_col1, rep_col2 = st.columns([0.25, 0.75])
#     with rep_col1:
#         if st.button("↔️ Replace base prompt"):
#             st.session_state["prompt_input"] = st.session_state["enhanced_prompt"]
#             st.success("Base prompt replaced with the enhanced version.")

# -----------------------------
# Upload Zone
# -----------------------------
st.markdown("### 🖼️ Reference Images (optional)")
uploaded_images = st.file_uploader(
    "Drop up to 3 images (order = priority)",
    type=["jpg", "jpeg", "png"],
    accept_multiple_files=True,
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
if gen_btn and "results" in st.session_state and st.session_state["results"]:
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
                        width='stretch',
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
