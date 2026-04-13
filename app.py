"""
Startup Shock Simulator - Crisis Management Game for Entrepreneurs
A high-stakes simulation where you manage ThermaLoop through 5 weeks of escalating crises.
"""

import streamlit as st
import time
import json
from typing import Dict, List, Tuple

# ============================================================================
# PAGE CONFIG & STYLING
# ============================================================================

st.set_page_config(
    page_title="Startup Shock Simulator",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS for purple accent and game styling
st.markdown("""
    <style>
    .crisis-card {
        border-left: 5px solid #7B2D8E;
        padding: 20px;
        background: linear-gradient(135deg, #f8f9fa 0%, #f0e6ff 100%);
        border-radius: 8px;
        margin: 15px 0;
    }
    .metric-box {
        text-align: center;
        padding: 20px;
        border-radius: 8px;
        background: #f8f9fa;
        font-weight: bold;
    }
    .option-button {
        padding: 15px;
        margin: 10px 0;
        border-left: 4px solid #7B2D8E;
        background: #f0e6ff;
        border-radius: 4px;
        cursor: pointer;
        font-weight: 500;
    }
    .impact-positive { color: #28a745; font-weight: bold; }
    .impact-negative { color: #dc3545; font-weight: bold; }
    .impact-neutral { color: #ffc107; font-weight: bold; }
    .timer-warning { color: #dc3545; font-weight: bold; font-size: 18px; }
    h1, h2, h3 { color: #7B2D8E; }
    </style>
""", unsafe_allow_html=True)

# ============================================================================
# GAME DATA & CONSTANTS
# ============================================================================

CRISES = {
    1: {
        "title": "👥 EARLY-STAGE MOMENT: Your First Real Hire",
        "narrative": "ThermaLoop is 180 customers and $12K MRR. You've been doing every job — sales, support, install logistics, fundraising email. You're burning out and opportunities are slipping. You have budget for exactly one full-time hire. Pick carefully: your first hire sets the DNA of the company.",
        "description": "Who do you bring on as your first employee? Your choice shapes the culture, the near-term metrics, and what you personally stop doing.",
        "options": [
            {
                "letter": "A",
                "title": "Senior Engineer",
                "description": "Hire a strong builder. Ship product faster, reduce founder coding time.",
                "impact": {"Founder Energy": +15, "Team Morale": +10, "Customer Satisfaction": +5, "Operational Capacity": +15, "Cash Position": -8000},
                "narrative_impact": "Product velocity doubles. You stop writing code at midnight, but the sales pipeline still only moves when you move it."
            },
            {
                "letter": "B",
                "title": "Operations Generalist",
                "description": "Hire a scrappy ops lead to own scheduling, vendor comms, customer onboarding.",
                "impact": {"Founder Energy": +25, "Team Morale": +10, "Customer Satisfaction": +15, "Operational Capacity": +25, "Cash Position": -6000},
                "narrative_impact": "Twelve of your recurring tasks disappear overnight. You get back four hours a day. The team is noticeably less chaotic."
            },
            {
                "letter": "C",
                "title": "Sales Hire",
                "description": "Hire a closer to drive new customer acquisition.",
                "impact": {"Founder Energy": +5, "Team Morale": +5, "Customer Satisfaction": 0, "Operational Capacity": +5, "Cash Position": -9000},
                "narrative_impact": "MRR grows modestly, but you're still the one handling onboarding, support, and ops. Hiring someone with no infrastructure to hand them leads doesn't pay off fast."
            },
            {
                "letter": "D",
                "title": "Stay Solo, Use Contractors",
                "description": "No FTE. Keep burn low. String together freelancers as needed.",
                "impact": {"Founder Energy": -15, "Team Morale": -10, "Customer Satisfaction": 0, "Operational Capacity": -5, "Cash Position": -1500},
                "narrative_impact": "Cheap but fragile. Every contractor has to be re-onboarded. You're still doing everything and quietly hitting the wall."
            }
        ],
        "worst_option": "D"
    },
    2: {
        "title": "🤝 EARLY-STAGE MOMENT: Cofounder Role Clarity",
        "narrative": "You and your cofounder have been grinding side-by-side for 6 months, but tensions are building. You both keep stepping on each other's work — duplicating sales calls, disagreeing on product priorities, and quietly resenting decisions the other made. A small argument about a customer refund just turned into a 90-minute fight about 'who actually runs what.'",
        "description": "Your cofounder relationship needs a reset. Roles were never formally defined. How do you handle it before it breaks the company?",
        "options": [
            {
                "letter": "A",
                "title": "Sit Down and Split Domains in Writing",
                "description": "Block a half-day together. Draw a clear line: you own product + ops, they own sales + customers. Document it. Review monthly.",
                "impact": {"Founder Energy": -5, "Team Morale": +20, "Customer Satisfaction": +5, "Operational Capacity": +15},
                "narrative_impact": "The conversation is hard but productive. Clear ownership unlocks both of you. Decisions get faster. The team exhales."
            },
            {
                "letter": "B",
                "title": "Avoid the Conversation, Stay Busy",
                "description": "You're both adults. Focus on the work. The tension will fade once you hit your next milestone.",
                "impact": {"Founder Energy": -25, "Team Morale": -20, "Customer Satisfaction": -5, "Operational Capacity": -15},
                "narrative_impact": "Nothing fades. The passive-aggression leaks into team meetings. An early hire quietly updates their resume."
            },
            {
                "letter": "C",
                "title": "Take Over Everything Yourself",
                "description": "You're the CEO. Push your cofounder into a narrower lane. Own the big calls.",
                "impact": {"Founder Energy": -35, "Team Morale": -15, "Customer Satisfaction": 0, "Cash Position": -2000},
                "narrative_impact": "Your cofounder feels sidelined. You're now the bottleneck for every decision. Burnout risk just spiked."
            },
            {
                "letter": "D",
                "title": "Bring in a Founder Coach",
                "description": "Hire a $2K/month founder coach to facilitate a structured alignment conversation over 3 sessions.",
                "impact": {"Founder Energy": +5, "Team Morale": +10, "Customer Satisfaction": 0, "Cash Position": -6000},
                "narrative_impact": "The coach helps you both see patterns. Expensive, but you come out aligned with a real operating agreement."
            }
        ],
        "worst_option": "B"
    },
    3: {
        "title": "🧱 EARLY-STAGE MOMENT: The Founder Bottleneck",
        "narrative": "You've noticed something uncomfortable: every decision — from which customer to email back to what color to use on the website — eventually lands on your desk. Your team of 3 keeps asking for your input. You're working 14-hour days and still falling behind. The team is capable, but they don't feel empowered to move without you.",
        "description": "You are the bottleneck. The team can't scale past you until you change how you delegate. What's your move?",
        "options": [
            {
                "letter": "A",
                "title": "Write a Simple Decision Framework",
                "description": "Spend a weekend documenting what decisions need you vs. what the team can own. Share it Monday. Trust them.",
                "impact": {"Founder Energy": +20, "Team Morale": +25, "Customer Satisfaction": +10, "Operational Capacity": +25},
                "narrative_impact": "The team surprises you. Within two weeks, they're making 70% of daily calls without escalating. You finally get to think strategically again."
            },
            {
                "letter": "B",
                "title": "Hire an Operations Lead",
                "description": "Post a job for an ops manager. Pay $90K base. They'll own the day-to-day so you don't have to.",
                "impact": {"Founder Energy": +10, "Team Morale": +5, "Customer Satisfaction": 0, "Cash Position": -15000},
                "narrative_impact": "The ops lead starts in 5 weeks. Until then, you're still the bottleneck, burning cash, and the team is still stuck waiting on you."
            },
            {
                "letter": "C",
                "title": "Power Through, You're the Only One Who Gets It",
                "description": "The team isn't ready. You'll keep making the calls until the company is bigger and hires are more senior.",
                "impact": {"Founder Energy": -45, "Team Morale": -25, "Customer Satisfaction": -10, "Operational Capacity": -20},
                "narrative_impact": "You hit the wall at week 4 — sick, exhausted, behind on everything. The team feels untrusted. Two quietly start interviewing."
            },
            {
                "letter": "D",
                "title": "Do a 'Founder-Free Week'",
                "description": "Block your calendar for one week. No decisions from you. The team runs the show. See what breaks.",
                "impact": {"Founder Energy": +15, "Team Morale": +15, "Customer Satisfaction": -5, "Operational Capacity": +10},
                "narrative_impact": "A few things wobble, but the team rises to it. You learn exactly which decisions actually need you — and which were just habit."
            }
        ],
        "worst_option": "C"
    },
    4: {
        "title": "💔 EARLY-STAGE MOMENT: Culture Crack",
        "narrative": "Your first hire just sent a long Slack DM: they feel the culture has shifted. Meetings run long, feedback is one-way, and nobody celebrates wins anymore. Two other team members quietly reacted with 💯. This is the first real signal that the team's energy is fraying — and you didn't see it coming.",
        "description": "The team's early energy is fading. Early culture signals matter more than anything else at your stage. What do you do?",
        "options": [
            {
                "letter": "A",
                "title": "Schedule 1:1s With Everyone This Week",
                "description": "Put 30 minutes with each team member on the calendar. Ask: what's working, what's not, what would you change tomorrow?",
                "impact": {"Founder Energy": -10, "Team Morale": +30, "Customer Satisfaction": +5, "Operational Capacity": +10},
                "narrative_impact": "You hear hard things. But people feel heard. Three concrete changes come out of the conversations. Trust compounds."
            },
            {
                "letter": "B",
                "title": "Send a Team-Wide Apology + Plan",
                "description": "Write a thoughtful message acknowledging the drift. Share 3 changes you'll make. Ship them this week.",
                "impact": {"Founder Energy": -5, "Team Morale": +15, "Customer Satisfaction": 0, "Operational Capacity": +5},
                "narrative_impact": "A public acknowledgment matters, but it's one-way communication. Some team members appreciate it, others want a real conversation."
            },
            {
                "letter": "C",
                "title": "Ignore It — Push Through the Sprint",
                "description": "You're 2 weeks from shipping the next release. Culture can wait. Results cure morale.",
                "impact": {"Founder Energy": -20, "Team Morale": -35, "Customer Satisfaction": -15, "Operational Capacity": -25},
                "narrative_impact": "You ship, but the best hire gives notice the following Monday. The team watches to see how you respond. This is the story they'll tell about you."
            },
            {
                "letter": "D",
                "title": "Plan a Team Offsite",
                "description": "Book a $6K offsite for 2 days next month. Get everyone out of the office. Rebuild connection.",
                "impact": {"Founder Energy": 0, "Team Morale": +10, "Customer Satisfaction": 0, "Cash Position": -6000},
                "narrative_impact": "The offsite is fun, but 'next month' is a long time when trust is fraying right now. You needed a quicker touch first."
            }
        ],
        "worst_option": "C"
    },
    5: {
        "title": "⚙️ EARLY-STAGE MOMENT: Processes That Scale",
        "narrative": "You're now 6 people and 220 customers. What worked at 3 people is breaking: onboarding is inconsistent, customer support lives in one person's head, and you just missed a renewal because nobody tracked it. Your team is good, but the lack of process is costing real money and real trust.",
        "description": "You've outgrown 'everyone figures it out.' The team needs light operating systems — without killing the scrappy energy. What's your approach?",
        "options": [
            {
                "letter": "A",
                "title": "Have the Team Build the Playbooks",
                "description": "Ask each person to document the top 3 things they do. Share back next Friday. You edit, not write.",
                "impact": {"Founder Energy": +10, "Team Morale": +20, "Customer Satisfaction": +20, "Operational Capacity": +30},
                "narrative_impact": "Ownership emerges organically. The playbooks aren't perfect, but they're real, used, and improved weekly. Renewals stop slipping through."
            },
            {
                "letter": "B",
                "title": "Write Every Process Yourself, Top-Down",
                "description": "You know how things should work. Lock yourself in for a week and write the company manual.",
                "impact": {"Founder Energy": -40, "Team Morale": -15, "Customer Satisfaction": +5, "Operational Capacity": +10},
                "narrative_impact": "You produce 40 pages nobody reads. The team feels micromanaged. The processes don't match how work actually happens."
            },
            {
                "letter": "C",
                "title": "Buy a SaaS Tool to Fix It",
                "description": "Sign up for a $400/mo ops platform. Configure it in a weekend. Tool-first approach.",
                "impact": {"Founder Energy": -10, "Team Morale": -5, "Customer Satisfaction": 0, "Cash Position": -4800},
                "narrative_impact": "The tool is powerful but misconfigured. Adoption is spotty. A tool doesn't solve a process problem — it just digitizes confusion."
            },
            {
                "letter": "D",
                "title": "Wait Until Something Breaks Badly",
                "description": "Process is bureaucracy. You'll formalize when the team is 15+. Until then, stay nimble.",
                "impact": {"Founder Energy": -15, "Team Morale": -10, "Customer Satisfaction": -25, "Operational Capacity": -30},
                "narrative_impact": "Three weeks later a customer gets double-billed, an onboarding falls apart, and a support ticket sits for 8 days. You're firefighting again."
            }
        ],
        "worst_option": "D"
    }
}

ARCHETYPES = {
    "The Firefighter": {
        "description": "You ran hot. Every crisis, you were in the thick of it, hands-on, leading the charge.",
        "traits": "High Founder Energy drain. You solved crises through sheer force of will. Your team respects your commitment but is burned out."
    },
    "The Delegator": {
        "description": "You trusted your team and preserved your energy for the big decisions.",
        "traits": "Low Founder Energy drain. You empowered others. Your team grew and remained motivated throughout the chaos."
    },
    "The Protector": {
        "description": "You prioritized your team's morale and wellbeing above all else.",
        "traits": "Team Morale stayed high. You created psychological safety, even when decisions were hard. Your team would follow you anywhere."
    },
    "The Pragmatist": {
        "description": "You optimized for cash position and long-term runway.",
        "traits": "You made tough calls that preserved capital. You may have sacrificed short-term metrics, but you kept the company alive."
    },
    "The Customer Champion": {
        "description": "You always prioritized customer satisfaction and brand.",
        "traits": "You doubled down on customer relationships. You built loyalty, but sometimes at the cost of internal efficiency."
    }
}

# ============================================================================
# SESSION STATE INITIALIZATION
# ============================================================================

def initialize_session_state():
    """Initialize all session state variables."""
    if "game_started" not in st.session_state:
        st.session_state.game_started = False
    if "current_week" not in st.session_state:
        st.session_state.current_week = 0
    if "metrics" not in st.session_state:
        st.session_state.metrics = {
            "Team Morale": 80,
            "Cash Position": 85000,
            "Customer Satisfaction": 75,
            "Operational Capacity": 80,
            "Founder Energy": 85
        }
    if "decision_history" not in st.session_state:
        st.session_state.decision_history = {}
    if "metric_history" not in st.session_state:
        st.session_state.metric_history = {i: None for i in range(1, 6)}
    if "decisions_made" not in st.session_state:
        st.session_state.decisions_made = 0
    if "disable_timer" not in st.session_state:
        st.session_state.disable_timer = False

initialize_session_state()

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def get_metric_color(value: int) -> str:
    """Return color based on metric value."""
    if value >= 70:
        return "#28a745"  # Green
    elif value >= 40:
        return "#ffc107"  # Yellow
    else:
        return "#dc3545"  # Red

def apply_impact(impact: Dict[str, int]):
    """Apply impact to metrics, capping between 0-100 for most, allowing any for Cash."""
    for metric, change in impact.items():
        if metric == "Cash Position":
            st.session_state.metrics[metric] += change
        else:
            new_value = st.session_state.metrics[metric] + change
            st.session_state.metrics[metric] = max(0, min(100, new_value))

def format_currency(value: int) -> str:
    """Format currency for display."""
    return f"${value:,.0f}"

def display_metrics():
    """Display the 5-metric dashboard."""
    cols = st.columns(5)
    with cols[0]:
        st.markdown(f"""
        <div class="metric-box">
            <div style="font-size: 14px; color: #666;">Team Morale</div>
            <div style="font-size: 32px; font-weight: bold; color: {get_metric_color(st.session_state.metrics['Team Morale'])};">
                {st.session_state.metrics['Team Morale']}
            </div>
        </div>
        """, unsafe_allow_html=True)
    with cols[1]:
        st.markdown(f"""
        <div class="metric-box">
            <div style="font-size: 14px; color: #666;">Cash Position</div>
            <div style="font-size: 24px; font-weight: bold; color: {get_metric_color(min(100, max(0, (st.session_state.metrics['Cash Position'] - 50000) // 500)))};word-break: break-word;">
                {format_currency(st.session_state.metrics['Cash Position'])}
            </div>
        </div>
        """, unsafe_allow_html=True)
    with cols[2]:
        st.markdown(f"""
        <div class="metric-box">
            <div style="font-size: 14px; color: #666;">Customer Satisfaction</div>
            <div style="font-size: 32px; font-weight: bold; color: {get_metric_color(st.session_state.metrics['Customer Satisfaction'])};">
                {st.session_state.metrics['Customer Satisfaction']}
            </div>
        </div>
        """, unsafe_allow_html=True)
    with cols[3]:
        st.markdown(f"""
        <div class="metric-box">
            <div style="font-size: 14px; color: #666;">Operational Capacity</div>
            <div style="font-size: 32px; font-weight: bold; color: {get_metric_color(st.session_state.metrics['Operational Capacity'])};">
                {st.session_state.metrics['Operational Capacity']}
            </div>
        </div>
        """, unsafe_allow_html=True)
    with cols[4]:
        st.markdown(f"""
        <div class="metric-box">
            <div style="font-size: 14px; color: #666;">Founder Energy</div>
            <div style="font-size: 32px; font-weight: bold; color: {get_metric_color(st.session_state.metrics['Founder Energy'])};">
                {st.session_state.metrics['Founder Energy']}
            </div>
        </div>
        """, unsafe_allow_html=True)

def display_crisis(week: int, crisis_data: Dict):
    """Display a crisis card."""
    st.markdown(f"""
    <div class="crisis-card">
        <h2 style="margin-top: 0;">{crisis_data['title']}</h2>
        <p style="font-size: 16px; color: #333; line-height: 1.6;">
            {crisis_data['narrative']}
        </p>
    </div>
    """, unsafe_allow_html=True)

def show_timed_decision(week: int, options: List[Dict]) -> str:
    """Display options with optional timer. Returns the selected option letter."""
    st.subheader("⏱️ Your Move (30 seconds)")

    # Disable timer checkbox
    st.session_state.disable_timer = st.checkbox(
        "Disable timer (accessibility)",
        value=st.session_state.disable_timer
    )

    if st.session_state.disable_timer:
        st.info("⏱️ Timer disabled. Take your time.")
        time_remaining = None
    else:
        time_remaining = 30

    # Create a container for the timer
    timer_placeholder = st.empty()

    # Display options as buttons
    st.markdown("### Choose your response:")
    choice = None
    cols = st.columns(2)

    for i, option in enumerate(options):
        col_idx = i % 2
        with cols[col_idx]:
            if st.button(
                f"**{option['letter']}. {option['title']}**\n\n{option['description']}",
                key=f"option_{week}_{option['letter']}"
            ):
                choice = option['letter']

    # Show timer if not disabled
    if not st.session_state.disable_timer:
        start_time = time.time()
        while choice is None and time.time() - start_time < 30:
            elapsed = int(time.time() - start_time)
            remaining = 30 - elapsed
            with timer_placeholder.container():
                progress = remaining / 30
                st.progress(progress)
                st.markdown(
                    f'<p class="timer-warning">⏳ Time remaining: {remaining} seconds</p>',
                    unsafe_allow_html=True
                )
            time.sleep(0.5)

        # Time expired
        if choice is None:
            crisis_data = CRISES[week]
            worst_option = crisis_data["worst_option"]
            choice = worst_option
            timer_placeholder.empty()
            st.warning(
                f"⏰ **Time's up!** Under pressure, you defaulted to **Option {choice}**. "
                f"This wasn't your best choice."
            )

    return choice

def display_option_details(option: Dict):
    """Display full details of a chosen option."""
    st.markdown(f"""
    ### Your Choice: **{option['letter']}. {option['title']}**

    {option['description']}
    """)

    st.markdown("#### Immediate Impact:")
    impact_cols = st.columns(5)
    impact_dict = option['impact']

    for i, (metric, change) in enumerate(impact_dict.items()):
        if i < 5:
            with impact_cols[i]:
                if change > 0:
                    st.markdown(f"<p class='impact-positive'>{metric}<br>+{change}</p>", unsafe_allow_html=True)
                elif change < 0:
                    st.markdown(f"<p class='impact-negative'>{metric}<br>{change}</p>", unsafe_allow_html=True)
                else:
                    st.markdown(f"<p class='impact-neutral'>{metric}<br>No change</p>", unsafe_allow_html=True)

    st.markdown(f"**Narrative Impact:** {option['narrative_impact']}")

def show_end_game_screen():
    """Display final results, archetype, and lessons."""
    st.markdown("---")
    st.title("🎮 GAME OVER: Your Startup Shock Survival Report")

    # Company Survival Score
    survival_score = sum([
        st.session_state.metrics["Team Morale"],
        st.session_state.metrics["Customer Satisfaction"],
        st.session_state.metrics["Operational Capacity"],
        st.session_state.metrics["Founder Energy"],
        min(100, (st.session_state.metrics["Cash Position"] - 50000) // 350)
    ]) / 5

    st.metric("Company Survival Score", f"{survival_score:.0f}/100")

    if survival_score >= 80:
        st.success("🌟 **THRIVING**: You navigated the chaos masterfully!")
    elif survival_score >= 60:
        st.info("💪 **SURVIVING**: You kept the company alive and learned hard lessons.")
    else:
        st.warning("⚠️ **STRUGGLING**: Your company is limping forward. Tough times ahead.")

    # Final Metrics
    st.subheader("📊 Final Metrics")
    display_metrics()

    # Founder Archetype
    st.subheader("🎭 Your Founder Archetype")
    archetype = determine_archetype()
    archetype_data = ARCHETYPES[archetype]
    st.markdown(f"""
    ### {archetype}

    {archetype_data['description']}

    **Your Pattern:** {archetype_data['traits']}
    """)

    # Cascade Visualization
    st.subheader("🔗 Decision Cascade Analysis")
    for week in range(1, 6):
        with st.expander(f"Week {week}: {CRISES[week]['title']}"):
            if week in st.session_state.decision_history:
                decision = st.session_state.decision_history[week]
                option = next(
                    (o for o in CRISES[week]['options'] if o['letter'] == decision),
                    None
                )
                if option:
                    st.markdown(f"**Your Choice:** {option['letter']}. {option['title']}")
                    st.markdown(f"**Impact Narrative:** {option['narrative_impact']}")
                    if week < 5:
                        next_week = week + 1
                        st.markdown(f"**Downstream Effect on Week {next_week}:**")
                        if option['impact'].get("Team Morale", 0) < -30:
                            st.markdown("🔴 Morale hit cascades into next week. Retention risk.")
                        if option['impact'].get("Cash Position", 0) < -10000:
                            st.markdown("💸 Cash burn accelerates. Tighter margins next week.")

    # Lessons Learned
    st.subheader("📚 Lessons Learned")
    lessons = generate_lessons()
    for i, lesson in enumerate(lessons, 1):
        st.markdown(f"**{i}. {lesson}**")

def determine_archetype() -> str:
    """Determine founder archetype based on decision patterns."""
    firefighter_score = 0
    delegator_score = 0
    protector_score = 0
    pragmatist_score = 0
    customer_score = 0

    for week, choice_letter in st.session_state.decision_history.items():
        options = {opt['letter']: opt for opt in CRISES[week]['options']}
        option = options.get(choice_letter)
        if not option:
            continue

        impact = option['impact']

        # Firefighter: high Founder Energy drain
        if impact.get("Founder Energy", 0) < -20:
            firefighter_score += 2

        # Delegator: low Founder Energy drain
        if impact.get("Founder Energy", 0) >= 0:
            delegator_score += 2

        # Protector: prioritized Team Morale
        if impact.get("Team Morale", 0) > 0:
            protector_score += 2

        # Pragmatist: prioritized Cash
        if impact.get("Cash Position", 0) > -5000 or (impact.get("Cash Position", 0) == 0 and impact.get("Founder Energy", 0) >= 0):
            pragmatist_score += 1

        # Customer Champion: prioritized Customer Satisfaction
        if impact.get("Customer Satisfaction", 0) > 10:
            customer_score += 2

    scores = {
        "The Firefighter": firefighter_score,
        "The Delegator": delegator_score,
        "The Protector": protector_score,
        "The Pragmatist": pragmatist_score,
        "The Customer Champion": customer_score
    }

    return max(scores, key=scores.get)

def generate_lessons() -> List[str]:
    """Generate personalized lessons based on patterns."""
    lessons = []

    # Analyze decision patterns
    energy_drained = sum(
        CRISES[w]['options'][next(i for i, o in enumerate(CRISES[w]['options']) if o['letter'] == d)]['impact'].get("Founder Energy", 0)
        for w, d in st.session_state.decision_history.items()
    )

    cash_burned = sum(
        -CRISES[w]['options'][next(i for i, o in enumerate(CRISES[w]['options']) if o['letter'] == d)]['impact'].get("Cash Position", 0)
        for w, d in st.session_state.decision_history.items()
    )

    morale_impact = sum(
        CRISES[w]['options'][next(i for i, o in enumerate(CRISES[w]['options']) if o['letter'] == d)]['impact'].get("Team Morale", 0)
        for w, d in st.session_state.decision_history.items()
    )

    if energy_drained < -50:
        lessons.append("You burned bright but burned out fast. Next time, trust your team to lead. Delegation isn't weakness—it's leverage.")

    if cash_burned > 30000:
        lessons.append("Cash is oxygen. You spent it trying to solve everything at once. Next time, be ruthless about spending. Every dollar matters.")

    if morale_impact < -40:
        lessons.append("Your team's morale tanked. People leave companies, not industries. Next time, make decisions WITH your team, not TO your team.")

    if len(lessons) < 3:
        lessons.append("You survived the gauntlet. Most founders never do. You learned that crisis management is about tradeoffs, not perfect solutions.")

    return lessons[:3]

# ============================================================================
# MAIN GAME FLOW
# ============================================================================

def main():
    """Main game loop."""
    # INTRO SCREEN
    if st.session_state.current_week == 0 and not st.session_state.game_started:
        st.title("⚡ STARTUP SHOCK SIMULATOR")
        st.markdown("""
        ## Crisis Management for Founders

        You founded **ThermaLoop**, a smart ventilation retrofit company. You've got traction. You've got a team.
        You've got $85K in the bank and 180 paying customers.

        Now comes the hard part: **surviving the chaos**.

        Over the next 5 weeks, your startup will face escalating crises. Each one will demand a choice.
        Each choice will cost you something. Your job isn't to avoid damage—it's to minimize it.

        ---

        ### 📋 Starting Position

        - **Company:** ThermaLoop (Smart Ventilation Retrofit Kits)
        - **Team:** 6 people (you + 5 employees)
        - **Monthly Revenue:** $12,000 MRR
        - **Cash in Bank:** $85,000
        - **Active Customers:** 180

        ### ⏱️ Time Estimate

        **~30-45 minutes** to complete this simulation.

        You'll face 5 crises over 5 weeks. Each decision has a 30-second timer (which you can disable). There's no "perfect" answer—only tradeoffs.

        ---

        ### 🎮 How It Works

        1. Each week brings a new crisis
        2. You'll see 3-4 response options
        3. Each option has different tradeoffs (sacrifice one metric to save another)
        4. Your choices cascade—decisions in Week 1 shape Week 2
        5. After Week 5, you'll get a survival score, founder archetype, and lessons learned

        **Ready?**
        """)

        if st.button("🚀 START SIMULATION", use_container_width=True, type="primary"):
            st.session_state.game_started = True
            st.session_state.current_week = 1
            st.rerun()

    # GAME WEEKS
    elif 1 <= st.session_state.current_week <= 5:
        week = st.session_state.current_week
        crisis_data = CRISES[week]

        st.title(f"WEEK {week} / 5")
        st.subheader(f"Company Status: ThermaLoop")

        display_metrics()

        st.markdown("---")
        display_crisis(week, crisis_data)

        # Decision making
        if week not in st.session_state.decision_history:
            # Show timer and get decision
            choice = show_timed_decision(week, crisis_data['options'])

            # Store decision
            st.session_state.decision_history[week] = choice
            st.session_state.decisions_made += 1

            # Apply impact
            selected_option = next(o for o in crisis_data['options'] if o['letter'] == choice)
            apply_impact(selected_option['impact'])

            st.rerun()
        else:
            # Show already-made decision
            choice = st.session_state.decision_history[week]
            selected_option = next(o for o in crisis_data['options'] if o['letter'] == choice)

            st.success(f"✅ Decision Made")
            display_option_details(selected_option)

            st.markdown("---")

            # Next week button
            if st.button(
                "Next Week →" if week < 5 else "See Final Report →",
                use_container_width=True,
                type="primary"
            ):
                if week < 5:
                    st.session_state.current_week += 1
                else:
                    st.session_state.current_week = 6
                st.rerun()

    # END GAME
    elif st.session_state.current_week == 6:
        show_end_game_screen()

        st.markdown("---")
        st.markdown("### Play Again?")
        if st.button("Restart Simulation", use_container_width=True):
            # Reset state
            st.session_state.game_started = False
            st.session_state.current_week = 0
            st.session_state.metrics = {
                "Team Morale": 80,
                "Cash Position": 85000,
                "Customer Satisfaction": 75,
                "Operational Capacity": 80,
                "Founder Energy": 85
            }
            st.session_state.decision_history = {}
            st.session_state.decisions_made = 0
            st.rerun()

if __name__ == "__main__":
    main()
