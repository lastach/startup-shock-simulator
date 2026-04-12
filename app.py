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
    page_icon="â¡",
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
        "title": "ð´ CRISIS ALERT: The Server Meltdown",
        "narrative": "Your viral social media post just brought 5,000 new signups in 2 hours. Your app is on fire... literally. The servers are down. Customers are furious. You have 30 seconds to act.",
        "description": "Unexpected traffic has crashed your infrastructure. Your team is panicking. Customers are getting error pages.",
        "options": [
            {
                "letter": "A",
                "title": "All-Hands Emergency Fix",
                "description": "Drop everything. You and the team code through the night.",
                "impact": {"Founder Energy": -25, "Team Morale": -15, "Customer Satisfaction": +30, "Cash Position": 0},
                "narrative_impact": "You crush the fix by 3 AM. Servers are back up. Customers forgive you... but everyone is exhausted."
            },
            {
                "letter": "B",
                "title": "Hire Emergency Contractor",
                "description": "Call in a $3K SRE specialist from Slack. Fast, professional, done.",
                "impact": {"Founder Energy": 0, "Team Morale": 0, "Customer Satisfaction": +20, "Cash Position": -3000},
                "narrative_impact": "The contractor fixes it in 4 hours. Costly, but your team gets rest. Your runway just got shorter."
            },
            {
                "letter": "C",
                "title": "Apologize & Schedule Fix",
                "description": "Go public with a transparent apology. Fix it next week.",
                "impact": {"Founder Energy": 0, "Team Morale": 0, "Customer Satisfaction": -30, "Cash Position": 0},
                "narrative_impact": "Your honesty is appreciated, but customers are skeptical. Some are churning. You bought time, but lost trust."
            },
            {
                "letter": "D",
                "title": "Emergency Weekend Sprint",
                "description": "Push the team for a weekend fix. Mandatory all-hands.",
                "impact": {"Founder Energy": -10, "Team Morale": -40, "Customer Satisfaction": +25, "Cash Position": 0},
                "narrative_impact": "It's fixed by Sunday, but your team is bitter. Resentment is building. People are talking about leaving."
            }
        ],
        "worst_option": "D"
    },
    2: {
        "title": "â ï¸ CRISIS ALERT: The Key Person Crisis",
        "narrative": "Your lead engineer (the only person who truly understands the codebase) just handed in their 2-week notice. They got an offer from a major tech company. Your entire technical foundation is walking out the door.",
        "description": "Your most critical team member is leaving. They're talented, irreplaceable, and going to a competitor. What do you do?",
        "options": [
            {
                "letter": "A",
                "title": "Aggressive Counter-Offer",
                "description": "Offer equity, salary bump, and a technical leadership role. Go big.",
                "impact": {"Founder Energy": 0, "Team Morale": +15, "Customer Satisfaction": 0, "Cash Position": -8000},
                "narrative_impact": "They stay! But you just burned $8K in cash and promised equity you may regret. Your runway compressed again."
            },
            {
                "letter": "B",
                "title": "Let Them Go Gracefully",
                "description": "Thank them for their contribution. Start the search for a replacement.",
                "impact": {"Founder Energy": 0, "Team Morale": -20, "Customer Satisfaction": 0, "Operational Capacity": -30},
                "narrative_impact": "The team respects your professionalism, but you've just lost critical capacity. Sprints will slow down for weeks."
            },
            {
                "letter": "C",
                "title": "Take Over Their Duties",
                "description": "You personally own their projects. You'll figure it out.",
                "impact": {"Founder Energy": -50, "Team Morale": 0, "Customer Satisfaction": -10, "Operational Capacity": +10},
                "narrative_impact": "You're drowning in code. Your attention splits everywhere. The business side of the company stalls."
            },
            {
                "letter": "D",
                "title": "Emergency Hiring Sprint",
                "description": "Offer $120K base + signing bonus. Hire fast.",
                "impact": {"Founder Energy": -15, "Team Morale": 0, "Customer Satisfaction": 0, "Cash Position": -15000},
                "narrative_impact": "You hire someone capable in 2 weeks, but they're learning on the job. Quality dips. You're in serious cash crunch territory."
            }
        ],
        "worst_option": "D"
    },
    3: {
        "title": "ð¥ CRISIS ALERT: The Supplier Squeeze",
        "narrative": "Your main component supplier just announced a 2x price increase effective immediately. Your hardware cost just doubled. Your margins are in freefall. You have 30 seconds to decide how to absorb this hit.",
        "description": "Your primary supplier has doubled their prices without warning. Your BOM (bill of materials) economics just broke. This is a margin killer.",
        "options": [
            {
                "letter": "A",
                "title": "Absorb the Cost",
                "description": "Eat the margin hit. Keep prices the same. Protect customer relationships.",
                "impact": {"Founder Energy": 0, "Team Morale": 0, "Customer Satisfaction": +10, "Cash Position": -12000},
                "narrative_impact": "Customers love you, but your unit economics are now terrible. Monthly burn is accelerating."
            },
            {
                "letter": "B",
                "title": "Pass the Cost to Customers",
                "description": "Raise prices by 30%. Let the market decide.",
                "impact": {"Founder Energy": 0, "Team Morale": 0, "Customer Satisfaction": -35, "Cash Position": 0},
                "narrative_impact": "You hit cash break-even, but customers are shocked. Churn accelerates. Some are looking at competitors."
            },
            {
                "letter": "C",
                "title": "Negotiate + Find Alternatives",
                "description": "Work the supplier relationship hard. Qualify an alternative. This takes your time.",
                "impact": {"Founder Energy": -30, "Team Morale": 0, "Customer Satisfaction": 0, "Cash Position": -4000},
                "narrative_impact": "You find a new supplier at 1.5x the original price. Better than 2x, but still a hit. You've bought yourself breathing room."
            },
            {
                "letter": "D",
                "title": "Redesign with Cheaper Components",
                "description": "Pivot the product. Substitute components for cheaper alternatives. Major engineering lift.",
                "impact": {"Founder Energy": -20, "Team Morale": -15, "Customer Satisfaction": -10, "Operational Capacity": -40},
                "narrative_impact": "You're stuck in a 6-week redesign. Features ship slower. The team is frustrated with the pivot."
            }
        ],
        "worst_option": "B"
    },
    4: {
        "title": "ð¨ CRISIS ALERT: The Customer Revolt",
        "narrative": "Two catastrophes hit simultaneously: Your biggest enterprise client (15% of revenue) is threatening to leave over a bug they found. AND a viral 1-star review just hit social media blasting your product. You have 30 seconds to choose. There is no good option hereâonly less bad ones.",
        "description": "Enterprise client revolt + viral negative review = existential threat. You must pick your poison.",
        "options": [
            {
                "letter": "A",
                "title": "All-In on Enterprise Client",
                "description": "Drop everything. Dedicate the team to fixing their issue. Ignore the viral review.",
                "impact": {"Founder Energy": -30, "Team Morale": -25, "Customer Satisfaction": -40, "Operational Capacity": -20},
                "narrative_impact": "You save the enterprise client, but the viral review spirals. Other customers start leaving. Your brand is damaged."
            },
            {
                "letter": "B",
                "title": "Address the Viral Review",
                "description": "Go public. Respond thoughtfully. Offer refunds. Control the narrative.",
                "impact": {"Founder Energy": -15, "Team Morale": 0, "Customer Satisfaction": -25, "Cash Position": -5000},
                "narrative_impact": "The review narrative softens, but the enterprise client feels abandoned. You may lose them anyway."
            },
            {
                "letter": "C",
                "title": "Split the Team",
                "description": "Half the team on enterprise client, half on damage control. Coordinate carefully.",
                "impact": {"Founder Energy": -25, "Team Morale": -30, "Customer Satisfaction": -20, "Operational Capacity": -25},
                "narrative_impact": "You address both, but nothing gets done well. Team feels scattered. Everyone is exhausted and frustrated."
            },
            {
                "letter": "D",
                "title": "Take a Deep Breath. Prioritize Strategically.",
                "description": "Enterprise client gets a personal call and roadmap for fixes. Public review gets a thoughtful, transparent response.",
                "impact": {"Founder Energy": -20, "Team Morale": -10, "Customer Satisfaction": -15, "Operational Capacity": -15},
                "narrative_impact": "You address both, acknowledging the pain. You don't fix everything, but people respect your composure."
            }
        ],
        "worst_option": "A"
    },
    5: {
        "title": "ð OPPORTUNITY BOMB: Acquisition Offer",
        "narrative": "A larger smart building company wants to acquire ThermaLoop for $2.5M. They're giving you 48 hours to decide. Your team is exhausted. Your runway is tight. This is the moment every founder dreams about... or nightmares about.",
        "description": "An acquisition offer has arrived in the chaos. $2.5M for ThermaLoop. 48 hours to decide. This is it.",
        "options": [
            {
                "letter": "A",
                "title": "Take the Deal",
                "description": "Accept the $2.5M offer. Cash out. Celebrate.",
                "impact": {"Founder Energy": 50, "Team Morale": 0, "Customer Satisfaction": 0, "Cash Position": 2500000},
                "narrative_impact": "You exit. You're a founder who built and sold a company. Success. But... was this the dream?"
            },
            {
                "letter": "B",
                "title": "Counter at $4M",
                "description": "Push back. You think you're worth more. Riskyâthey might walk.",
                "impact": {"Founder Energy": -20, "Team Morale": 0, "Customer Satisfaction": 0, "Cash Position": 0},
                "narrative_impact": "They walk away. You're back to the grind with a demoralized team and an uncertain future."
            },
            {
                "letter": "C",
                "title": "Decline and Double Down",
                "description": "Turn it down. You're going for unicorn status. Build independently.",
                "impact": {"Founder Energy": -40, "Team Morale": +50, "Customer Satisfaction": 0, "Operational Capacity": 0},
                "narrative_impact": "Your team rallies behind the vision. But the pressure is immense. The next 18 months will be brutal."
            },
            {
                "letter": "D",
                "title": "Ask for 2 More Weeks",
                "description": "Negotiate more time. Get your team's input. Make a deliberate choice.",
                "impact": {"Founder Energy": -10, "Team Morale": +20, "Customer Satisfaction": 0, "Cash Position": 0},
                "narrative_impact": "They grant 2 weeks. You bring the team into the decision. Whatever you choose feels like your choice, not their deadline."
            }
        ],
        "worst_option": "B"
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
    st.subheader("â±ï¸ Your Move (30 seconds)")

    # Disable timer checkbox
    st.session_state.disable_timer = st.checkbox(
        "Disable timer (accessibility)",
        value=st.session_state.disable_timer
    )

    if st.session_state.disable_timer:
        st.info("â±ï¸ Timer disabled. Take your time.")
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
                    f'<p class="timer-warning">â³ Time remaining: {remaining} seconds</p>',
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
                f"â° **Time's up!** Under pressure, you defaulted to **Option {choice}**. "
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
    st.title("ð® GAME OVER: Your Startup Shock Survival Report")

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
        st.success("ð **THRIVING**: You navigated the chaos masterfully!")
    elif survival_score >= 60:
        st.info("ðª **SURVIVING**: You kept the company alive and learned hard lessons.")
    else:
        st.warning("â ï¸ **STRUGGLING**: Your company is limping forward. Tough times ahead.")

    # Final Metrics
    st.subheader("ð Final Metrics")
    display_metrics()

    # Founder Archetype
    st.subheader("ð­ Your Founder Archetype")
    archetype = determine_archetype()
    archetype_data = ARCHETYPES[archetype]
    st.markdown(f"""
    ### {archetype}

    {archetype_data['description']}

    **Your Pattern:** {archetype_data['traits']}
    """)

    # Cascade Visualization
    st.subheader("ð Decision Cascade Analysis")
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
                        st.markdown(f"**Downstream Effect on Week {next_week}:** ", end="")
                        if option['impact'].get("Team Morale", 0) < -30:
                            st.markdown("ð´ Morale hit cascades into next week. Retention risk.")
                        if option['impact'].get("Cash Position", 0) < -10000:
                            st.markdown("ð¸ Cash burn accelerates. Tighter margins next week.")

    # Lessons Learned
    st.subheader("ð Lessons Learned")
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
        lessons.append("You burned bright but burned out fast. Next time, trust your team to lead. Delegation isn't weaknessâit's leverage.")

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
        st.title("â¡ STARTUP SHOCK SIMULATOR")
        st.markdown("""
        ## Crisis Management for Founders

        You founded **ThermaLoop**, a smart ventilation retrofit company. You've got traction. You've got a team.
        You've got $85K in the bank and 180 paying customers.

        Now comes the hard part: **surviving the chaos**.

        Over the next 5 weeks, your startup will face escalating crises. Each one will demand a choice.
        Each choice will cost you something. Your job isn't to avoid damageâit's to minimize it.

        ---

        ### ð Starting Position

        - **Company:** ThermaLoop (Smart Ventilation Retrofit Kits)
        - **Team:** 6 people (you + 5 employees)
        - **Monthly Revenue:** $12,000 MRR
        - **Cash in Bank:** $85,000
        - **Active Customers:** 180

        ### â±ï¸ Time Estimate

        **~30-45 minutes** to play through all 5 crises.

        Each decision has a 30-second timer (which you can disable). There's no "perfect" answerâonly tradeoffs.

        ---

        ### ð® How It Works

        1. Each week brings a new crisis
        2. You'll see 3-4 response options
        3. Each option has different tradeoffs (sacrifice one metric to save another)
        4. Your choices cascadeâdecisions in Week 1 shape Week 2
        5. After Week 5, you'll get a survival score, founder archetype, and lessons learned

        **Ready?**
        """)

        if st.button("ð START SIMULATION", use_container_width=True, type="primary"):
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

            st.success(f"â Decision Made")
            display_option_details(selected_option)

            st.markdown("---")

            # Next week button
            if st.button(
                "Next Week â" if week < 5 else "See Final Report â",
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
