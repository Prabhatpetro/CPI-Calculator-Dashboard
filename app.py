import math
import re
from decimal import ROUND_HALF_UP, Decimal

import streamlit as st

st.set_page_config(page_title="CPI/SPI Calculator", page_icon="🎓", layout="centered")

st.markdown(
    """
    <style>
    .stApp {
        background: linear-gradient(135deg, #1a1c2e 0%, #2b1f4a 50%, #1a1c2e 100%);
        background-attachment: fixed;
    }
    div[data-testid="stForm"] {
        background: rgba(255, 255, 255, 0.04);
        border: 1px solid rgba(255, 255, 255, 0.12) !important;
        border-radius: 18px !important;
        padding: 1.75rem 1.5rem 1rem 1.5rem;
        box-shadow: 0 8px 28px rgba(0, 0, 0, 0.28);
        backdrop-filter: blur(8px);
    }

    @media (prefers-color-scheme: light) {
        .stApp {
            background: linear-gradient(135deg, #f4f6ff 0%, #eceffb 50%, #f4f6ff 100%);
        }
        div[data-testid="stForm"] {
            background: rgba(255, 255, 255, 0.75);
            border: 1px solid rgba(0, 0, 0, 0.08) !important;
            box-shadow: 0 8px 28px rgba(0, 0, 0, 0.08);
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

NAME_PATTERN = re.compile(r"^[A-Za-z\s]+$")

if "step" not in st.session_state:
    st.session_state.step = 0
    st.session_state.data = {}


def semester_to_year_label(semester):
    year = (semester - 1) // 2 + 1
    suffix = {1: "1st", 2: "2nd", 3: "3rd"}.get(year, f"{year}th")
    return f"{suffix} Year"


def reset():
    st.session_state.step = 0
    st.session_state.data = {}


def _rounded_top_rect(x, y, w, h, r=4):
    r = min(r, h)
    return (
        f"M{x:.2f},{y + r:.2f} "
        f"Q{x:.2f},{y:.2f} {x + r:.2f},{y:.2f} "
        f"L{x + w - r:.2f},{y:.2f} "
        f"Q{x + w:.2f},{y:.2f} {x + w:.2f},{y + r:.2f} "
        f"L{x + w:.2f},{y + h:.2f} "
        f"L{x:.2f},{y + h:.2f} Z"
    )


def render_comparison_chart(current_cpi, current_spi, target_cpi, spi_needed, achievable):
    bars = [
        ("Current CPI", current_cpi, "#2a78d6", "#3987e5"),
        ("Current SPI", current_spi, "#eb6834", "#d95926"),
        ("Target CPI", target_cpi, "#1baf7a", "#199e70"),
        (
            "SPI Needed",
            spi_needed,
            "#0ca30c" if achievable else "#d03b3b",
            "#0ca30c" if achievable else "#d03b3b",
        ),
    ]

    max_val = max(10.0, spi_needed)
    if max_val <= 10:
        y_max, y_step = 10, 2
    else:
        raw_step = (max_val * 1.05) / 5
        magnitude = 10 ** math.floor(math.log10(raw_step))
        y_step = next(
            mult * magnitude for mult in (1, 2, 5, 10) if mult * magnitude >= raw_step
        )
        y_max = math.ceil((max_val * 1.05) / y_step) * y_step

    svg_w, svg_h = 560, 300
    m_top, m_right, m_bottom, m_left = 34, 24, 44, 40
    plot_w = svg_w - m_left - m_right
    plot_h = svg_h - m_top - m_bottom
    baseline_y = m_top + plot_h

    n = len(bars)
    slot_w = plot_w / n
    bar_w = 24

    gridlines = []
    for gv in range(0, int(y_max) + 1, int(y_step)):
        gy = baseline_y - (gv / y_max) * plot_h
        gridlines.append(
            f'<line x1="{m_left}" y1="{gy:.2f}" x2="{m_left + plot_w}" y2="{gy:.2f}" '
            f'class="gridline" />'
            f'<text x="{m_left - 8}" y="{gy + 4:.2f}" class="tick-label" text-anchor="end">{gv}</text>'
        )

    bar_shapes = []
    for i, (label, value, color_light, color_dark) in enumerate(bars):
        x_center = m_left + slot_w * i + slot_w / 2
        x = x_center - bar_w / 2
        bar_h = max(2.0, (value / y_max) * plot_h)
        y = baseline_y - bar_h
        path = _rounded_top_rect(x, y, bar_w, bar_h)
        label_y = max(y - 8, m_top - 6)
        bar_shapes.append(
            f'<path d="{path}" class="bar" '
            f'style="--bar-light:{color_light}; --bar-dark:{color_dark};" '
            f'data-label="{label}" data-value="{value:.2f}" tabindex="0" />'
            f'<text x="{x_center:.2f}" y="{label_y:.2f}" class="value-label" '
            f'text-anchor="middle">{value:.2f}</text>'
            f'<text x="{x_center:.2f}" y="{baseline_y + 20:.2f}" class="cat-label" '
            f'text-anchor="middle">{label}</text>'
        )

    html = f"""
    <div class="viz-root" id="cpi-chart-root">
      <style>
        .viz-root {{
          color-scheme: light;
          --surface-1: #fcfcfb;
          --text-primary: #0b0b0b;
          --text-secondary: #52514e;
          --muted: #898781;
          --gridline: #e1e0d9;
          --baseline: #c3c2b7;
          font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
        }}
        @media (prefers-color-scheme: dark) {{
          .viz-root {{
            color-scheme: dark;
            --surface-1: #1a1a19;
            --text-primary: #ffffff;
            --text-secondary: #c3c2b7;
            --muted: #898781;
            --gridline: #2c2c2a;
            --baseline: #383835;
          }}
        }}
        .viz-root svg {{ width: 100%; height: {svg_h}px; display: block; }}
        .viz-root .gridline {{ stroke: var(--gridline); stroke-width: 1; }}
        .viz-root .tick-label, .viz-root .cat-label {{
          fill: var(--muted); font-size: 11px;
        }}
        .viz-root .value-label {{
          fill: var(--text-primary); font-size: 12px; font-weight: 600;
        }}
        .viz-root .bar {{
          fill: var(--bar-light);
          cursor: pointer;
          transition: filter 0.15s ease;
        }}
        @media (prefers-color-scheme: dark) {{
          .viz-root .bar {{ fill: var(--bar-dark); }}
        }}
        .viz-root .bar:hover, .viz-root .bar:focus {{
          filter: brightness(1.12);
          outline: none;
          stroke: var(--surface-1);
          stroke-width: 2px;
        }}
        .viz-root .baseline {{ stroke: var(--baseline); stroke-width: 1; }}
        .viz-root .tooltip {{
          position: absolute;
          pointer-events: none;
          background: var(--surface-1);
          color: var(--text-primary);
          border: 1px solid var(--gridline);
          border-radius: 8px;
          padding: 6px 10px;
          font-size: 12px;
          box-shadow: 0 4px 16px rgba(0,0,0,0.18);
          opacity: 0;
          transition: opacity 0.1s ease;
          white-space: nowrap;
        }}
        .viz-root .tooltip .tt-value {{ font-weight: 700; }}
        .viz-root .tooltip .tt-label {{ color: var(--text-secondary); margin-left: 4px; }}
      </style>
      <div style="position: relative;">
        <svg viewBox="0 0 {svg_w} {svg_h}" preserveAspectRatio="none">
          {''.join(gridlines)}
          <line x1="{m_left}" y1="{baseline_y}" x2="{m_left + plot_w}" y2="{baseline_y}" class="baseline" />
          {''.join(bar_shapes)}
        </svg>
        <div class="tooltip" id="tt"></div>
      </div>
      <script>
        (function() {{
          const root = document.getElementById('cpi-chart-root');
          const tt = root.querySelector('#tt');
          root.querySelectorAll('.bar').forEach(function(bar) {{
            function show(e) {{
              const label = bar.getAttribute('data-label');
              const value = bar.getAttribute('data-value');
              tt.innerHTML = '';
              const strong = document.createElement('span');
              strong.className = 'tt-value';
              strong.textContent = value;
              const secondary = document.createElement('span');
              secondary.className = 'tt-label';
              secondary.textContent = label;
              tt.appendChild(strong);
              tt.appendChild(secondary);
              tt.style.opacity = '1';
              const rect = root.getBoundingClientRect();
              const bx = bar.getBoundingClientRect();
              tt.style.left = (bx.left - rect.left + bx.width / 2) + 'px';
              tt.style.top = (bx.top - rect.top - 36) + 'px';
            }}
            function hide() {{ tt.style.opacity = '0'; }}
            bar.addEventListener('pointerenter', show);
            bar.addEventListener('pointermove', show);
            bar.addEventListener('focus', show);
            bar.addEventListener('pointerleave', hide);
            bar.addEventListener('blur', hide);
          }});
        }})();
      </script>
    </div>
    """
    st.iframe(html, height=svg_h + 20)


if st.session_state.step == 0:
    title_col, icon_col = st.columns([5, 1])
    with title_col:
        st.title("🎓 CPI/SPI Calculator")
    with icon_col:
        st.markdown(
            "<div style='font-size:3.5rem; text-align:right; margin-top:0.6rem;'>🧮</div>",
            unsafe_allow_html=True,
        )
else:
    st.title("🎓 CPI/SPI Calculator")

STEP_LABELS = ["Enter your details", "Current status", "Your target", "Result"]
_current_step = st.session_state.step
st.caption(f"Step {_current_step + 1} of {len(STEP_LABELS)}: {STEP_LABELS[_current_step]}")
st.progress((_current_step + 1) / len(STEP_LABELS))

# ---------- Step 0: Landing / user details ----------
if st.session_state.step == 0:
    st.subheader("Enter your details")
    with st.form("landing_form"):
        name = st.text_input("Name")
        roll_no = st.text_input("Roll No")
        college = st.text_input("College Name")
        submitted = st.form_submit_button("Next")

    if submitted:
        if not name.strip() or not roll_no.strip() or not college.strip():
            st.error("Please fill in all fields.")
        elif not NAME_PATTERN.match(name.strip()):
            st.error("Please Enter The Proper Name")
        elif not NAME_PATTERN.match(college.strip()):
            st.error("Please Enter The Proper Name")
        elif len(name.strip()) < 3 or len(college.strip()) < 3:
            st.error("Please enter the valid details")
        elif name.strip().lower() == college.strip().lower():
            st.error("Name and College Name cannot be the same.")
        else:
            st.session_state.data.update(name=name, roll_no=roll_no, college=college)
            st.session_state.step = 1
            st.rerun()

# ---------- Step 1: Current status ----------
elif st.session_state.step == 1:
    st.subheader("Your current status")
    with st.form("inputs_form"):
        current_semester = st.number_input(
            "Current Semester", min_value=1, max_value=8, step=1, value=1
        )
        st.caption(f"➡ {semester_to_year_label(current_semester)}")
        current_cpi = st.number_input(
            "Current CPI", step=0.01, format="%.2f"
        )
        current_spi = st.number_input(
            "Current SPI", step=0.01, format="%.2f"
        )
        col1, col2 = st.columns(2)
        with col1:
            back = st.form_submit_button("Back")
        with col2:
            submitted = st.form_submit_button("Next")

    if back:
        st.session_state.step = 0
        st.rerun()

    if submitted:
        if not (0 <= current_cpi <= 10) or not (0 <= current_spi <= 10):
            st.error("Invalid input, please input correct value")
        else:
            st.session_state.data.update(
                current_semester=current_semester,
                current_cpi=current_cpi,
                current_spi=current_spi,
            )
            st.session_state.step = 2
            st.rerun()

# ---------- Step 2: Target ----------
elif st.session_state.step == 2:
    subheader_col, emoji_col = st.columns([5, 1])
    with subheader_col:
        st.subheader("Your target")
    with emoji_col:
        st.markdown(
            "<div style='font-size:2.5rem; text-align:right;'>🎯</div>",
            unsafe_allow_html=True,
        )
    current_semester = st.session_state.data["current_semester"]
    with st.form("target_form"):
        target_semester = st.number_input(
            "Target Semester", min_value=1, max_value=8, step=1, value=8
        )
        st.caption(f"➡ {semester_to_year_label(target_semester)}")
        target_cpi = st.number_input(
            "Target CPI", step=0.01, format="%.2f"
        )
        col1, col2 = st.columns(2)
        with col1:
            back = st.form_submit_button("Back")
        with col2:
            submitted = st.form_submit_button("Calculate")

    if back:
        st.session_state.step = 1
        st.rerun()

    if submitted:
        if not (0 <= target_cpi <= 10):
            st.error("Invalid input, please input correct value")
        elif target_semester <= current_semester:
            st.error("Target Semester must be after your Current Semester.")
        else:
            st.session_state.data.update(
                target_semester=target_semester,
                target_cpi=target_cpi,
            )
            st.session_state.step = 3
            st.rerun()

# ---------- Step 3: Result ----------
elif st.session_state.step == 3:
    d = st.session_state.data
    remaining_semesters = d["target_semester"] - d["current_semester"]
    target_cpi = Decimal(str(d["target_cpi"]))
    current_cpi = Decimal(str(d["current_cpi"]))
    spi_needed = (
        target_cpi * d["target_semester"] - current_cpi * d["current_semester"]
    ) / Decimal(remaining_semesters)
    spi_needed = spi_needed.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    with st.container(border=True):
        subheader_col, emoji_col = st.columns([5, 1])
        with subheader_col:
            st.subheader(f"Result for {d['name']} ({d['roll_no']})")
        with emoji_col:
            st.markdown(
                "<div style='font-size:2.5rem; text-align:right;'>🔍</div>",
                unsafe_allow_html=True,
            )
        st.caption(d["college"])

        st.metric(
            label=f"SPI needed per semester (next {remaining_semesters} semester"
            f"{'s' if remaining_semesters > 1 else ''})",
            value=f"{spi_needed:.2f}",
        )

        achievable = spi_needed <= 10

        render_comparison_chart(
            current_cpi=float(current_cpi),
            current_spi=float(d["current_spi"]),
            target_cpi=float(target_cpi),
            spi_needed=float(spi_needed),
            achievable=achievable,
        )

        with st.expander("View as table"):
            st.table(
                {
                    "Metric": ["Current CPI", "Current SPI", "Target CPI", "SPI Needed"],
                    "Value": [
                        f"{float(current_cpi):.2f}",
                        f"{float(d['current_spi']):.2f}",
                        f"{float(target_cpi):.2f}",
                        f"{float(spi_needed):.2f}",
                    ],
                }
            )

        if achievable:
            st.success("GO and GRIND! 💪 Your target is achievable.")
        else:
            st.error("Sorry, not possible — this target needs a hypothetical SPI above 10.")

    st.divider()
    if st.button("Calculate Again"):
        reset()
        st.rerun()
