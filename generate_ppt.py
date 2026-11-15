import sys
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.enum.shapes import MSO_SHAPE

def create_presentation():
    prs = Presentation()
    
    # Configure slide size to widescreen (16:9)
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    
    # Define color palette
    c_navy = RGBColor(30, 58, 138)       # #1E3A8A - primary
    c_emerald = RGBColor(16, 185, 129)   # #10B981 - accent
    c_black = RGBColor(17, 24, 39)       # #111827 - text
    c_gray = RGBColor(107, 114, 128)     # #6B7280 - muted
    c_white = RGBColor(255, 255, 255)
    c_light_bg = RGBColor(249, 250, 251) # #F9FAFB
    
    # Helper: Set font formatting
    def format_text(run, font_name="Segoe UI", size_pt=13, bold=False, italic=False, color=c_black):
        run.font.name = font_name
        run.font.size = Pt(size_pt)
        run.font.bold = bold
        run.font.italic = italic
        run.font.color.rgb = color

    # Helper: Add background card/shapes to slides for premium design
    def add_slide_header(slide, title_text, category_text="GRAPHSHIELD CORE ARCHITECTURE"):
        # Category tag
        tx_box = slide.shapes.add_textbox(Inches(0.5), Inches(0.2), Inches(12), Inches(0.3))
        tf = tx_box.text_frame
        tf.word_wrap = True
        tf.margin_left = tf.margin_top = tf.margin_bottom = tf.margin_right = 0
        p = tf.paragraphs[0]
        r = p.add_run()
        r.text = category_text.upper()
        format_text(r, font_name="Arial", size_pt=10, bold=True, color=c_emerald)
        
        # Main Title
        tx_box_title = slide.shapes.add_textbox(Inches(0.5), Inches(0.4), Inches(12), Inches(0.8))
        tf_title = tx_box_title.text_frame
        tf_title.word_wrap = True
        tf_title.margin_left = tf_title.margin_top = tf_title.margin_bottom = tf_title.margin_right = 0
        p_title = tf_title.paragraphs[0]
        r_title = p_title.add_run()
        r_title.text = title_text
        format_text(r_title, font_name="Arial Black", size_pt=26, bold=True, color=c_navy)

    # Helper: Add structured bullets to a text frame
    def add_bullet(tf, title, desc, indent=0, size_t=13, size_d=12):
        p = tf.add_paragraph() if tf.paragraphs[0].text else tf.paragraphs[0]
        p.space_after = Pt(8)
        p.level = indent
        
        r_title = p.add_run()
        r_title.text = "• " + title + ": "
        format_text(r_title, font_name="Segoe UI", size_pt=size_t, bold=True, color=c_navy)
        
        r_desc = p.add_run()
        r_desc.text = desc
        format_text(r_desc, font_name="Segoe UI", size_pt=size_d, color=c_black)

    # -------------------------------------------------------------
    # SLIDE 1: Title Slide (Layout: Blank - custom designed)
    # -------------------------------------------------------------
    slide1 = prs.slides.add_slide(prs.slide_layouts[6])
    
    # Deep Navy background shape
    bg_shape = slide1.shapes.add_shape(
        MSO_SHAPE.RECTANGLE, Inches(0), Inches(0), Inches(13.333), Inches(7.5)
    )
    bg_shape.fill.solid()
    bg_shape.fill.fore_color.rgb = c_navy
    bg_shape.line.fill.background()
    
    # Left Column Title
    tx_title = slide1.shapes.add_textbox(Inches(0.8), Inches(1.8), Inches(6.0), Inches(4.5))
    tf1 = tx_title.text_frame
    tf1.word_wrap = True
    tf1.margin_left = tf1.margin_top = tf1.margin_bottom = tf1.margin_right = 0
    
    p1 = tf1.paragraphs[0]
    r1 = p1.add_run()
    r1.text = "GRAPHSHIELD"
    format_text(r1, font_name="Arial Black", size_pt=54, bold=True, color=c_white)
    
    p2 = tf1.add_paragraph()
    r2 = p2.add_run()
    r2.text = "Real-Time Hybrid Threat Detection for Role-Based Banking Applications"
    format_text(r2, font_name="Segoe UI", size_pt=18, bold=False, color=c_emerald)
    
    # Right Column Info Box
    tx_right = slide1.shapes.add_textbox(Inches(7.2), Inches(1.8), Inches(5.3), Inches(4.5))
    tf_right = tx_right.text_frame
    tf_right.word_wrap = True
    tf_right.margin_left = tf_right.margin_top = tf_right.margin_bottom = tf_right.margin_right = 0
    
    p_info1 = tf_right.paragraphs[0]
    r_info1 = p_info1.add_run()
    r_info1.text = "Academic & Implementation Overview"
    format_text(r_info1, font_name="Segoe UI", size_pt=16, bold=True, color=c_white)
    
    p_info2 = tf_right.add_paragraph()
    p_info2.space_before = Pt(12)
    r_info2 = p_info2.add_run()
    r_info2.text = "This presentation details the full deployment structure and integration pipeline of the GraphShield threat detection system.\n\n" \
                  "• Stage 1: Tabular Biometric Analytics (LightGBM)\n" \
                  "• Stage 2: Relational Network Graph Mapping (Neo4j)\n" \
                  "• Stage 3: Explainable Risk Matrix Generation (TreeSHAP)\n" \
                  "• Architecture: Decoupled Zero-Latency Dual-Flow Orchestrator\n" \
                  "• Production: Flask WSGI (Render) | Flutter Client (Vercel) | MongoDB Atlas"
    format_text(r_info2, font_name="Segoe UI", size_pt=12, color=c_light_bg)

    # -------------------------------------------------------------
    # SLIDE 2: 1. Introduction (Expanded)
    # -------------------------------------------------------------
    slide2 = prs.slides.add_slide(prs.slide_layouts[6])
    add_slide_header(slide2, "1. Introduction to GraphShield")
    
    # Left Column: Vulnerabilities & Scope
    tx_left2 = slide2.shapes.add_textbox(Inches(0.5), Inches(1.3), Inches(5.8), Inches(5.5))
    tf_left2 = tx_left2.text_frame
    tf_left2.word_wrap = True
    add_bullet(tf_left2, "Vulnerability of Isolated Auth", 
               "Standard authentication checks credentials in isolation, leaving systems blind to network context. It fails to identify coordinated credential stuffing, botnets, and device takeover attempts.",
               size_t=14, size_d=13)
    add_bullet(tf_left2, "The Limits of Tabular ML", 
               "Supervised classifiers evaluate static metrics (e.g. typing speed) but miss user-to-device-to-IP relationships. This allows distributed attacks using normal behavioral traits to slip past standard ML engines.",
               size_t=14, size_d=13)
    add_bullet(tf_left2, "The Regulatory Demand for XAI", 
               "Financial compliance standards (such as GDPR and Basel III) require complete transparency into why an automated security engine blocks a user's transaction or login request.",
               size_t=14, size_d=13)
    
    # Right Column: Proposed Paradigm
    tx_right2 = slide2.shapes.add_textbox(Inches(6.8), Inches(1.3), Inches(6.0), Inches(5.5))
    tf_right2 = tx_right2.text_frame
    tf_right2.word_wrap = True
    add_bullet(tf_right2, "The Hybrid Security Architecture", 
               "Fuses supervised ML scoring (LightGBM), unsupervised anomaly detection (Isolation Forest), and relational link analysis (Neo4j Graph Database) to score login risk on multiple planes.",
               size_t=14, size_d=13)
    add_bullet(tf_right2, "Zero-Latency Dual-Flow Design", 
               "Decouples client authentication from heavy AI inference. The API returns an ALLOW verdict in ~4ms while offloading the scoring, graph updates, and explainability calculations to an async background worker.",
               size_t=14, size_d=13)
    add_bullet(tf_right2, "TreeSHAP Local Explanations", 
               "Integrates TreeSHAP natively to generate feature-level risk explanations in real-time, displaying attributions (e.g., Typing Speed: 30%) on detail panels for banking operators.",
               size_t=14, size_d=13)

    # -------------------------------------------------------------
    # SLIDE 3: 2. Dataset Collection & Description (Expanded)
    # -------------------------------------------------------------
    slide3 = prs.slides.add_slide(prs.slide_layouts[6])
    add_slide_header(slide3, "2. Dataset Collection & Description")
    
    # Left Column: Features & Attributes
    tx_left3 = slide3.shapes.add_textbox(Inches(0.5), Inches(1.3), Inches(5.8), Inches(5.5))
    tf_left3 = tx_left3.text_frame
    tf_left3.word_wrap = True
    add_bullet(tf_left3, "Ingested Telemetry Features", 
               "Fuses diverse biometrics, network variables, and hardware properties collected at client login entry-points.",
               size_t=14, size_d=13)
    add_bullet(tf_left3, "  - Behavioral Metrics", 
               "Typing speed (chars/sec), average request interval, and session duration aggregates.",
               size_t=13, size_d=12)
    add_bullet(tf_left3, "  - Network & Security Headers", 
               "Client IP address, VPN detection registry matching, and IP change frequency metrics.",
               size_t=13, size_d=12)
    add_bullet(tf_left3, "  - Hardware Fingerprinting", 
               "Browser signatures including OS, platform, user agent details, and screen resolution hashed into a unique device ID.",
               size_t=13, size_d=12)

    # Right Column: Dataset Characteristics
    tx_right3 = slide3.shapes.add_textbox(Inches(6.8), Inches(1.3), Inches(6.0), Inches(5.5))
    tf_right3 = tx_right3.text_frame
    tf_right3.word_wrap = True
    add_bullet(tf_right3, "12,000 Login Sessions Dataset", 
               "Calculated using 12,000 distinct operational session logs. Contains representative user behaviors and diverse simulated threat models (credential stuffing, botnets, and hijackers).",
               size_t=14, size_d=13)
    add_bullet(tf_right3, "Incremental Aggregation Engine", 
               "Backend feature engineering runs on the fly by querying MongoDB to aggregate the last 10 login sessions for the target user ID and bank, updating historical aggregates in milliseconds.",
               size_t=14, size_d=13)
    add_bullet(tf_right3, "Active Graph Entity Mapping", 
               "Vertices (User, Device, IP, Bank) and edges (USES, CONNECTED_TO, BELONGS_TO) are stored to dynamically represent the live relationship topology.",
               size_t=14, size_d=13)

    # -------------------------------------------------------------
    # SLIDE 4: 3. Proposed System (Expanded)
    # -------------------------------------------------------------
    slide4 = prs.slides.add_slide(prs.slide_layouts[6])
    add_slide_header(slide4, "3. Proposed Detection Engine")
    
    # Left Column: Tabular scoring (S_ml)
    tx_left4 = slide4.shapes.add_textbox(Inches(0.5), Inches(1.3), Inches(5.8), Inches(5.5))
    tf_left4 = tx_left4.text_frame
    tf_left4.word_wrap = True
    add_bullet(tf_left4, "Supervised & Anomaly scoring", 
               "Fuses two tabular engines to evaluate biometrics:\n" \
               "S_ml = 0.7 * P_lgbm + 0.3 * S_anomaly\n" \
               "This allows supervised precision while maintaining unsupervised coverage for novel attacks.",
               size_t=14, size_d=13)
    add_bullet(tf_left4, "LightGBM Classifier (P_lgbm)", 
               "Outputs supervised classification probabilities based on typing speed, failed logins, and request interval distributions.",
               size_t=14, size_d=13)
    add_bullet(tf_left4, "Isolation Forest (S_anomaly)", 
               "Unsupervised anomaly engine flagging outliers in session characteristics and device variables, outputting 1.0 for anomalous records.",
               size_t=14, size_d=13)
    
    # Right Column: Graph scoring (S_g) & Decision
    tx_right4 = slide4.shapes.add_textbox(Inches(6.8), Inches(1.3), Inches(6.0), Inches(5.5))
    tf_right4 = tx_right4.text_frame
    tf_right4.word_wrap = True
    add_bullet(tf_right4, "Relational Graph Engine (S_g)", 
               "Evaluates Neo4j metrics for: device reuse count (+0.4 if >2 users), IP rotation count (+0.3 if >3 IPs), and cross-bank footprints (+0.5 if >1 bank). Max score is capped at 1.0.",
               size_t=14, size_d=13)
    add_bullet(tf_right4, "Consolidated Decision Logic", 
               "Final Score S_final = 0.5 * S_ml + 0.5 * S_g.\n" \
               "Decision is BLOCK if S_final >= 0.5, else ALLOW. Equal weighting ensures both biometrics and graph edges must align.",
               size_t=14, size_d=13)
    add_bullet(tf_right4, "TreeSHAP Local Explainability", 
               "Runs predict(..., pred_contrib=True) on LightGBM. Decomposes trees to extract exact feature contributions, allowing live UI explanation widgets.",
               size_t=14, size_d=13)

    # -------------------------------------------------------------
    # SLIDE 5: 4. System Architecture / Workflow (Expanded)
    # -------------------------------------------------------------
    slide5 = prs.slides.add_slide(prs.slide_layouts[6])
    add_slide_header(slide5, "4. System Architecture & Workflow")
    
    # Left Column: Synchronous Telemetry Path
    tx_left5 = slide5.shapes.add_textbox(Inches(0.5), Inches(1.3), Inches(5.8), Inches(5.5))
    tf_left5 = tx_left5.text_frame
    tf_left5.word_wrap = True
    add_bullet(tf_left5, "User Ingestion & Middleware intercept", 
               "User submits login. Node.js Demo Bank middleware captures biometrics and posts telemetry to Flask orchestrator. API key is validated via headers.",
               size_t=14, size_d=13)
    add_bullet(tf_left5, "Zero-Latency API Response", 
               "Flask API assigns a unique session ID, logs the transaction, and returns an immediate ALLOW response (4ms latency) so authentication is not blocked.",
               size_t=14, size_d=13)
    add_bullet(tf_left5, "Immutable S3 raw Backup", 
               "The orchestrator immediately uploads the raw JSON telemetry payload and metadata headers to s3://graphshield-storage-bucket/SESSION_ID/raw/ to create an audit trace.",
               size_t=14, size_d=13)

    # Right Column: Asynchronous Threat Evaluation
    tx_right5 = slide5.shapes.add_textbox(Inches(6.8), Inches(1.3), Inches(6.0), Inches(5.5))
    tf_right5 = tx_right5.text_frame
    tf_right5.word_wrap = True
    add_bullet(tf_right5, "Asynchronous Background Thread", 
               "A daemon worker thread is triggered in the background. It reads the raw S3 payload, engineering dynamic rolling features via MongoDB query lookups.",
               size_t=14, size_d=13)
    add_bullet(tf_right5, "Parallel Inference & Graph Queries", 
               "Runs ML tabular scoring and Graph DB Bolt logs in parallel via ThreadPoolExecutor. Graph edges are saved via Cypher scripts to S3 /graph/.",
               size_t=14, size_d=13)
    add_bullet(tf_right5, "Consolidated S3 /alerts/ & DB Logging", 
               "Writes the final decision JSON and TreeSHAP matrix to S3 /alerts/. Saves the risk event to MongoDB, updating UI dashboards in real-time.",
               size_t=14, size_d=13)

    # -------------------------------------------------------------
    # SLIDE 6: 5. Modules of the System (Expanded)
    # -------------------------------------------------------------
    slide6 = prs.slides.add_slide(prs.slide_layouts[6])
    add_slide_header(slide6, "5. Modules of the System")
    
    # Left Column: Frontend Portals
    tx_left6 = slide6.shapes.add_textbox(Inches(0.5), Inches(1.3), Inches(5.8), Inches(5.5))
    tf_left6 = tx_left6.text_frame
    tf_left6.word_wrap = True
    add_bullet(tf_left6, "1. Frontend Dashboard Portals", 
               "Built with Flutter. Separate portals for User (session details, device/IP lists), Bank (customer approvals, trials), and Admin (global threat maps, graph visualizers).",
               size_t=14, size_d=13)
    add_bullet(tf_left6, "2. API Orchestration Layer", 
               "Flask API backend server handling token checks (JWT), Redis rate-limit validations, CORS preflight controls, and background thread executions.",
               size_t=14, size_d=13)
    add_bullet(tf_left6, "3. Mock AWS S3 storage client", 
               "A local filesystem-based simulated S3 client structured with /raw/, /extracted/, /graph/, and /alerts/ buckets to store diagnostic audit traces.",
               size_t=14, size_d=13)

    # Right Column: Engines & Analyzers
    tx_right6 = slide6.shapes.add_textbox(Inches(6.8), Inches(1.3), Inches(6.0), Inches(5.5))
    tf_right6 = tx_right6.text_frame
    tf_right6.word_wrap = True
    add_bullet(tf_right6, "4. Feature Engineering Engine", 
               "Extracts user biometrics, device hashes, and network IPs. Queries MongoDB to aggregate rolling aggregates (failed attempts, request intervals).",
               size_t=14, size_d=13)
    add_bullet(tf_right6, "5. Machine Learning Analyzer", 
               "Loads trained pickle models. Evaluates supervised LightGBM and unsupervised Isolation Forest anomaly scoring.",
               size_t=14, size_d=13)
    add_bullet(tf_right6, "6. Graph Analytics & XAI Module", 
               "Maps relational coordinates via Cypher queries to Neo4j. Traverses LightGBM booster paths via TreeSHAP to calculate feature attributions.",
               size_t=14, size_d=13)

    # -------------------------------------------------------------
    # SLIDE 7: 6. System Implementation & Integration (Expanded)
    # -------------------------------------------------------------
    slide7 = prs.slides.add_slide(prs.slide_layouts[6])
    add_slide_header(slide7, "6. System Implementation & Integration")
    
    # Left Column: Backend Stack
    tx_left7 = slide7.shapes.add_textbox(Inches(0.5), Inches(1.3), Inches(5.8), Inches(5.5))
    tf_left7 = tx_left7.text_frame
    tf_left7.word_wrap = True
    add_bullet(tf_left7, "Production Flask Backend", 
               "Implemented in Python 3.11 with Flask, CORS, PyJWT, and bcrypt. Serves concurrent sessions under Gunicorn WSGI for production-ready Render hosting.",
               size_t=14, size_d=13)
    add_bullet(tf_left7, "MongoDB Atlas Data Layer", 
               "MongoDB stores user credentials, active subscriptions, and risk events. Includes a mock graph fallback storing nodes and edges if Neo4j is offline.",
               size_t=14, size_d=13)
    add_bullet(tf_left7, "Neo4j Graph Database Bolt Driver", 
               "Neo4j parses graph nodes. Executes Cypher queries to map IP-to-device relationships and flag suspicious cross-bank activities.",
               size_t=14, size_d=13)

    # Right Column: Middleware & Client
    tx_right7 = slide7.shapes.add_textbox(Inches(6.8), Inches(1.3), Inches(6.0), Inches(5.5))
    tf_right7 = tx_right7.text_frame
    tf_right7.word_wrap = True
    add_bullet(tf_right7, "Node.js Middleware Integration", 
               "Developed Express-based middleware (services/graphShield.js) in the Demo Bank. Intercepts auth to pass biometric hashes to GraphShield dynamically.",
               size_t=14, size_d=13)
    add_bullet(tf_right7, "Flutter Web Engine", 
               "Dart-compiled client application with custom HTTP services, cached JWT tokens, fl_chart visualizations, and graphview layouts.",
               size_t=14, size_d=13)
    add_bullet(tf_right7, "Redis Session Cache", 
               "Redis (or MockRedis fallback) handles rate limiting and token blacklisting to prevent auth abuse and brute-forcing.",
               size_t=14, size_d=13)

    # -------------------------------------------------------------
    # SLIDE 8: 7. Experimental Results & Outputs (Expanded)
    # -------------------------------------------------------------
    slide8 = prs.slides.add_slide(prs.slide_layouts[6])
    add_slide_header(slide8, "7. Experimental Results & Model Metrics")
    
    # Left Column: Accuracy Metrics Table
    rows, cols = 6, 2
    left, top, width, height = Inches(0.5), Inches(1.3), Inches(5.8), Inches(2.2)
    table_shape = slide8.shapes.add_table(rows, cols, left, top, width, height)
    table = table_shape.table
    
    headers = ["Evaluation Metric", "Value (12,000 Sessions)"]
    for c, text in enumerate(headers):
        cell = table.cell(0, c)
        cell.text = text
        cell.fill.solid()
        cell.fill.fore_color.rgb = c_navy
        for p in cell.text_frame.paragraphs:
            p.alignment = PP_ALIGN.LEFT
            for r in p.runs:
                format_text(r, font_name="Segoe UI", size_pt=13, bold=True, color=c_white)
                
    metrics_data = [
        ["Detection Accuracy", "94.43%"],
        ["Precision (Positive Predictive Value)", "89.70%"],
        ["Recall (Sensitivity / True Positive Rate)", "91.86%"],
        ["F1 Score", "90.77%"],
        ["False Positive Rate (FPR)", "4.47%"]
    ]
    
    for r_idx, row_data in enumerate(metrics_data):
        for c_idx, val in enumerate(row_data):
            cell = table.cell(r_idx + 1, c_idx)
            cell.text = val
            cell.fill.solid()
            cell.fill.fore_color.rgb = c_light_bg if r_idx % 2 == 0 else c_white
            for p in cell.text_frame.paragraphs:
                p.alignment = PP_ALIGN.LEFT
                for r in p.runs:
                    format_text(r, font_name="Segoe UI", size_pt=12, bold=(c_idx == 1), color=c_black)

    # Bullet point below the table
    tx_below_table = slide8.shapes.add_textbox(Inches(0.5), Inches(3.8), Inches(5.8), Inches(3.2))
    tf_below = tx_below_table.text_frame
    tf_below.word_wrap = True
    add_bullet(tf_below, "Model Evaluation Metrics", 
               "Calculated over a validation set of 12,000 login sessions. Demonstrates excellent accuracy (94.43%) and a low false positive rate (4.47%).",
               size_t=13, size_d=12)
    add_bullet(tf_below, "Coordinated Botnet Mitigation", 
               "Flags login sequences where a single IP address or device fingerprint is rotated across multiple user identities in under 10 seconds.",
               size_t=13, size_d=12)

    # Right Column: Latency & Threat Scenarios
    tx_right8 = slide8.shapes.add_textbox(Inches(6.8), Inches(1.3), Inches(6.0), Inches(5.5))
    tf_right8 = tx_right8.text_frame
    tf_right8.word_wrap = True
    add_bullet(tf_right8, "Synchronous API Latency", 
               "API endpoint (/security/check-login) responds in ~4.19 ms, avoiding any transaction blocking or delays for users.",
               size_t=14, size_d=13)
    add_bullet(tf_right8, "Asynchronous Pipeline Duration", 
               "The complete background scoring pipeline takes ~1.7 seconds, including history aggregation, parallel ML & Graph checks, and S3 outputs.",
               size_t=14, size_d=13)
    add_bullet(tf_right8, "Mitigated Hijacking Scenarios", 
               "Flagged credential stuffing and account takeovers when user features (typing speed, login hour, VPN) mismatched their historical profile.",
               size_t=14, size_d=13)
    add_bullet(tf_right8, "TreeSHAP Validation", 
               "Successfully outputs user-facing percentage breakdowns of risk features (e.g. typing speed accounts for 30% of risk) for operators.",
               size_t=14, size_d=13)

    # -------------------------------------------------------------
    # SLIDE 9: 8. Conclusion (Expanded)
    # -------------------------------------------------------------
    slide9 = prs.slides.add_slide(prs.slide_layouts[6])
    add_slide_header(slide9, "8. Conclusion & Future Work")
    
    # Left Column: Key Accomplishments
    tx_left9 = slide9.shapes.add_textbox(Inches(0.5), Inches(1.3), Inches(5.8), Inches(5.5))
    tf_left9 = tx_left9.text_frame
    tf_left9.word_wrap = True
    add_bullet(tf_left9, "Eliminated Transaction Latency", 
               "Decoupled threat scoring from the authentication path via an asynchronous worker design. Resolves the trade-off between transaction speed and security evaluation depth.",
               size_t=14, size_d=13)
    add_bullet(tf_left9, "Explainable AI (XAI) Compliance", 
               "Integrating TreeSHAP local explanations satisfies strict banking audit requirements and increases administrator trust in automated decisions.",
               size_t=14, size_d=13)
    add_bullet(tf_left9, "Graph Enrichment Benefits", 
               "Adding graph edge mapping captures botnets and IP-device rotation patterns that standard tabular classifiers miss.",
               size_t=14, size_d=13)
    
    # Right Column: Future Directions
    tx_right9 = slide9.shapes.add_textbox(Inches(6.8), Inches(1.3), Inches(6.0), Inches(5.5))
    tf_right9 = tx_right9.text_frame
    tf_right9.word_wrap = True
    add_bullet(tf_right9, "Render, Vercel, & Atlas Deployment", 
               "Migrating from local mock environments to production-ready servers (Render backend, Vercel frontend, and MongoDB Atlas databases).",
               size_t=14, size_d=13)
    add_bullet(tf_right9, "Graph Scaling with Neo4j GDS", 
               "Plan to incorporate Neo4j Graph Data Science (GDS) algorithms like PageRank and Louvain community detection to spot fraudulent clusters.",
               size_t=14, size_d=13)
    add_bullet(tf_right9, "Automated MFA Escalation", 
               "Configuring the system to trigger multi-factor challenges automatically if the risk score exceeds defined thresholds.",
               size_t=14, size_d=13)

    # Save
    prs.save("GraphShield_Presentation.pptx")
    print("Presentation created successfully as 'GraphShield_Presentation.pptx'")

if __name__ == '__main__':
    create_presentation()
