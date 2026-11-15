import os
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, Image, Flowable, Preformatted
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas

# WIDESCREEN / PAGE CONFIGURATION
PAGE_WIDTH, PAGE_HEIGHT = letter

# -------------------------------------------------------------
# INDEX PAGE ENTRIES CONFIGURATION (Easily Editable)
# -------------------------------------------------------------
INDEX_ENTRIES = [
    {"title": "INDEX", "page": "1", "is_chapter": True},
    {"title": "ABSTRACT", "page": "2", "is_chapter": True},
    {"title": "CHAPTER 1: INTRODUCTION", "page": "3", "is_chapter": True},
    {"title": "CHAPTER 2: BACKGROUND LITERATURE", "page": "3", "is_chapter": True},
    {"title": "CHAPTER 3: PROBLEM STATEMENT AND OBJECTIVES", "page": "4", "is_chapter": True},
    {"title": "3.1 Problem Statement", "page": "", "is_chapter": False},
    {"title": "3.2 Objectives", "page": "", "is_chapter": False},
    {"title": "CHAPTER 4: SOLUTION METHODOLOGY", "page": "6", "is_chapter": True},
    {"title": "4.1 System Workflow", "page": "", "is_chapter": False},
    {"title": "4.2 Dual-Flow API and Async Worker Setup", "page": "", "is_chapter": False},
    {"title": "4.3 S3 Simulated Object Store Layout", "page": "", "is_chapter": False},
    {"title": "4.4 Dynamic Feature Engineering Module", "page": "", "is_chapter": False},
    {"title": "4.5 LightGBM Supervised Risk Classification", "page": "", "is_chapter": False},
    {"title": "4.6 Isolation Forest Unsupervised Anomaly Scoring", "page": "", "is_chapter": False},
    {"title": "4.7 Neo4j Graph Relational Mapping", "page": "", "is_chapter": False},
    {"title": "4.8 Parallel Inference & Decision Orchestration", "page": "", "is_chapter": False},
    {"title": "4.9 TreeSHAP Local Attributions", "page": "", "is_chapter": False},
    {"title": "4.10 Database Persistence & Storage", "page": "", "is_chapter": False},
    {"title": "4.11 UI Portals and Dashboard Module", "page": "", "is_chapter": False},
    {"title": "CHAPTER 5: IMPLEMENTATION", "page": "9", "is_chapter": True},
    {"title": "5.1 User Authentication", "page": "", "is_chapter": False},
    {"title": "5.2 Data Collection and Session Monitoring", "page": "", "is_chapter": False},
    {"title": "5.3 Feature Engineering", "page": "", "is_chapter": False},
    {"title": "5.4 Machine Learning-Based Fraud Detection", "page": "", "is_chapter": False},
    {"title": "5.5 Anomaly Detection", "page": "", "is_chapter": False},
    {"title": "5.6 Graph Intelligence Analysis", "page": "", "is_chapter": False},
    {"title": "5.7 Hybrid Risk Scoring", "page": "", "is_chapter": False},
    {"title": "5.8 Explainable AI Integration", "page": "", "is_chapter": False},
    {"title": "5.9 Database Storage", "page": "", "is_chapter": False},
    {"title": "5.10 Core Decision Engine Implementation", "page": "", "is_chapter": False},
    {"title": "CHAPTER 6: PRESENTATION OF RESULTS", "page": "11", "is_chapter": True},
    {"title": "6.1 User Authentication Performance", "page": "", "is_chapter": False},
    {"title": "6.2 Machine Learning-Based Fraud Detection", "page": "", "is_chapter": False},
    {"title": "6.3 Anomaly Detection Performance", "page": "", "is_chapter": False},
    {"title": "6.4 Graph Intelligence Analysis", "page": "", "is_chapter": False},
    {"title": "6.5 Explainable AI Results", "page": "", "is_chapter": False},
    {"title": "6.6 Risk Score Generation", "page": "", "is_chapter": False},
    {"title": "6.7 Overall System Performance", "page": "", "is_chapter": False},
    {"title": "6.8 Admin Dashboard Interface", "page": "", "is_chapter": False},
    {"title": "6.9 User Portal and Authentication Interface", "page": "", "is_chapter": False},
    {"title": "CHAPTER 7: PERFORMANCE ANALYSIS", "page": "16", "is_chapter": True},
    {"title": "7.1 Authentication Performance", "page": "", "is_chapter": False},
    {"title": "7.2 Machine Learning Performance", "page": "", "is_chapter": False},
    {"title": "7.3 Anomaly Detection Performance", "page": "", "is_chapter": False},
    {"title": "7.4 Graph Intelligence Performance", "page": "", "is_chapter": False},
    {"title": "7.5 Overall System Performance", "page": "", "is_chapter": False},
    {"title": "7.6 Performance Comparison Tables", "page": "", "is_chapter": False},
    {"title": "7.7 Performance Metrics Comparison Chart", "page": "", "is_chapter": False},
    {"title": "CHAPTER 8: APPLICATIONS", "page": "20", "is_chapter": True},
    {"title": "CHAPTER 9: FUTURE SCOPE", "page": "22", "is_chapter": True},
    {"title": "CHAPTER 10: CONCLUSION", "page": "24", "is_chapter": True},
    {"title": "REFERENCES", "page": "25", "is_chapter": True}
]

# Dictionary to store measured page numbers for each chapter
CHAPTER_PAGES = {}

# Page Tracker flowable to record page numbers during layout
class PageTracker(Flowable):
    def __init__(self, key, page_dict):
        Flowable.__init__(self)
        self.key = key
        self.page_dict = page_dict

    def draw(self):
        if self.page_dict is not None:
            self.page_dict[self.key] = self.canv._pageNumber

    def wrap(self, availWidth, availHeight):
        return 0, 0

# Custom Canvas class to handle two-pass page numbering
class NumberedCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        super(NumberedCanvas, self).__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super(NumberedCanvas, self).showPage()
        super(NumberedCanvas, self).save()

    def draw_page_decorations(self, page_count):
        # Header (drawn on all pages)
        self.saveState()
        self.setFont("Times-Roman", 10)
        self.setFillColor(colors.black)
        self.drawRightString(7.75 * inch, 10.45 * inch, "Graph Shield: Security Purpose Security Engine")
        
        # Double Header separator lines (brown/dark red color)
        self.setStrokeColor(colors.HexColor("#5F191B"))
        self.setLineWidth(1.5)
        self.line(inch * 0.75, 10.37 * inch, 7.75 * inch, 10.37 * inch)
        self.setLineWidth(0.75)
        self.line(inch * 0.75, 10.32 * inch, 7.75 * inch, 10.32 * inch)
        
        # Footer
        self.setFont("Times-Bold", 10)
        self.setFillColor(colors.black)
        self.drawString(inch * 0.75, 0.5 * inch, "CSE DEPT, GMU DVG")
        self.drawRightString(7.75 * inch, 0.5 * inch, f"Page {self._pageNumber}")
        
        # Footer separator line
        self.setStrokeColor(colors.HexColor("#5F191B"))
        self.setLineWidth(1.0)
        self.line(inch * 0.75, 0.6 * inch, 7.75 * inch, 0.6 * inch)
        self.restoreState()

def build_story(styles, page_dict=None):
    style_h1 = styles['Heading1_Custom']
    style_h2 = styles['Heading2_Custom']
    style_body = styles['Body_Custom']
    style_bullet = styles['Bullet_Custom']
    style_ref = styles['Ref_Custom']
    
    # Asset paths
    assets_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")
    workflow_img_path = os.path.join(assets_dir, "workflow_flowchart.png")
    admin_img_path = os.path.join(assets_dir, "admin_dashboard.jpg")
    user_img_path = os.path.join(assets_dir, "user_panel.jpg")
    login_img_path = os.path.join(assets_dir, "login_panel.jpg")
    perf_img_path = os.path.join(assets_dir, "performance_chart.png")

    story = []

    # -------------------------------------------------------------
    # INDEX PAGE (Page 1)
    # -------------------------------------------------------------
    # Create a compact title style for the index to save space
    style_index_title = ParagraphStyle(
        name='IndexTitle',
        parent=style_h1,
        spaceAfter=5
    )
    story.append(Paragraph("INDEX", style_index_title))
    story.append(Spacer(1, 5))
    
    index_table_data = []
    t_styles = [
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 0),
        ('TOPPADDING', (0,0), (-1,-1), 0),
    ]
    
    for idx, entry in enumerate(INDEX_ENTRIES):
        title = entry["title"]
        page = entry["page"]
        
        # If we have dynamic page numbers from pass 1, use them
        if page_dict and title in page_dict:
            page = str(page_dict[title])
            
        if entry["is_chapter"]:
            # Chapter items: Bold, times, dot leaders if page exists
            dots = ""
            if page:
                dots = "." * 55
            
            index_table_data.append([title, dots, page])
            t_styles.append(('FONTNAME', (0, idx), (-1, idx), 'Times-Bold'))
            t_styles.append(('FONTSIZE', (0, idx), (-1, idx), 10))
        else:
            # Sub-heading items: Indented, regular, no page numbers
            indent_title = "    " + title
            index_table_data.append([indent_title, "", ""])
            t_styles.append(('FONTNAME', (0, idx), (-1, idx), 'Times-Roman'))
            t_styles.append(('FONTSIZE', (0, idx), (-1, idx), 9))
            
    index_table = Table(index_table_data, colWidths=[3.8*inch, 2.7*inch, 0.5*inch])
    index_table.setStyle(TableStyle(t_styles))
    story.append(index_table)
    story.append(PageBreak())

    # -------------------------------------------------------------
    # ABSTRACT
    # -------------------------------------------------------------
    story.append(PageTracker("ABSTRACT", page_dict))
    story.append(Paragraph("ABSTRACT", style_h1))
    abstract_text = (
        "With the rapid expansion of digital banking and online financial transactions, securing authentication pipelines against "
        "sophisticated, automated, and coordinated cyber threats is paramount. Traditional authentication models rely heavily on "
        "static credentials, leaving systems vulnerable to credential stuffing, account takeovers, and bot-driven attacks. This "
        "report presents GraphShield, an intelligent, multi-layered security engine designed to detect and mitigate fraudulent login "
        "attempts in real-time. GraphShield implements a dual-flow architecture that delivers low-latency authentication decisions "
        "synchronously while executing detailed behavioral and graph intelligence analysis asynchronously in the background. The "
        "framework combines a LightGBM classifier for supervised tabular risk scoring, an Isolation Forest detector for unsupervised "
        "anomaly scoring, and a Neo4j graph database layer to uncover hidden relationships and IP rotation patterns. Furthermore, "
        "TreeSHAP explainability is integrated to decompose model weights into transparent, percentage-based feature attributions, "
        "enabling auditability and trust. Evaluated over 12,000 active sessions, the GraphShield framework achieves a classification "
        "accuracy of 94.43%, a precision of 89.70%, a recall of 91.86%, and a false positive rate of 4.47%, presenting a robust and "
        "scalable solution for modern digital banking infrastructures."
    )
    story.append(Paragraph(abstract_text, style_body))
    story.append(PageBreak())

    # -------------------------------------------------------------
    # CHAPTER 1: INTRODUCTION
    # -------------------------------------------------------------
    story.append(PageTracker("CHAPTER 1: INTRODUCTION", page_dict))
    story.append(Paragraph("CHAPTER 1: INTRODUCTION", style_h1))
    intro_p1 = (
        "With the rapid growth of digital banking and online financial services, securing user accounts "
        "against fraud, account takeovers, and unauthorized access has become a critical challenge. "
        "Traditional authentication systems primarily rely on static credentials such as usernames, "
        "passwords, and one-time passwords (OTPs). While these mechanisms verify user identity, "
        "they often fail to analyze behavioral patterns, device trustworthiness, and hidden relationships "
        "among fraudulent activities, making them vulnerable to sophisticated cyberattacks."
    )
    intro_p2 = (
        "GraphShield is an intelligent banking security and fraud detection framework designed to "
        "enhance authentication by combining Machine Learning (ML), Anomaly Detection, Graph "
        "Intelligence, and Explainable Artificial Intelligence (XAI). The system continuously "
        "evaluates user behavior, device characteristics, network attributes, and historical login "
        "patterns to identify suspicious activities in real time."
    )
    intro_p3 = (
        "The proposed framework employs a hybrid scoring engine that integrates a LightGBM "
        "classifier and an Isolation Forest anomaly detector to generate risk scores for each login "
        "session. In addition, a Neo4j-based graph intelligence layer analyzes relationships between "
        "devices, IP addresses, and user accounts to uncover coordinated fraud patterns that may "
        "remain undetected by conventional methods."
    )
    intro_p4 = (
        "To maintain a seamless user experience, GraphShield follows a dual-flow architecture in "
        "which authentication decisions are delivered instantly, while advanced threat analysis is "
        "executed asynchronously in the background. Furthermore, TreeSHAP-based explainability "
        "provides transparent insights into the factors influencing risk predictions, improving trust and "
        "auditability."
    )
    intro_p5 = (
        "By integrating predictive analytics, graph-based fraud detection, and explainable AI, "
        "GraphShield offers a scalable, secure, and efficient solution for modern banking "
        "environments, enabling financial institutions to proactively detect threats while minimizing "
        "disruption to legitimate users."
    )
    intro_p6 = (
        "The increasing sophistication of cyber threats in the banking sector has highlighted the need "
        "for intelligent security systems capable of adapting to evolving attack patterns. Fraudsters "
        "often exploit stolen credentials, compromised devices, VPN networks, and automated bot "
        "attacks to bypass traditional authentication mechanisms. As financial institutions process "
        "millions of transactions and login attempts daily, manually identifying suspicious activities "
        "becomes impractical. Therefore, advanced data-driven approaches that leverage machine "
        "learning and behavioral analytics are essential for detecting anomalies and reducing financial "
        "losses."
    )
    intro_p7 = (
        "Modern banking systems require proactive security mechanisms that can identify threats "
        "before they result in financial loss or unauthorized access. GraphShield enhances security by "
        "continuously monitoring user activities and evaluating potential risks in real time."
    )
    story.append(Paragraph(intro_p1, style_body))
    story.append(Paragraph(intro_p2, style_body))
    story.append(Paragraph(intro_p3, style_body))
    story.append(Paragraph(intro_p4, style_body))
    story.append(Paragraph(intro_p5, style_body))
    story.append(Paragraph(intro_p6, style_body))
    story.append(Paragraph(intro_p7, style_body))
    story.append(PageBreak())

    # -------------------------------------------------------------
    # CHAPTER 2: BACKGROUND LITERATURE (Page 3)
    # -------------------------------------------------------------
    story.append(PageTracker("CHAPTER 2: BACKGROUND LITERATURE", page_dict))
    story.append(Paragraph("CHAPTER 2: BACKGROUND LITERATURE", style_h1))
    lit_p1 = (
        "The rapid growth of digital banking and online financial services has increased the "
        "importance of secure authentication and fraud detection mechanisms. Traditional banking "
        "systems primarily rely on passwords, OTPs, and device-based authentication methods to "
        "verify user identity. Although these approaches provide basic security, they often fail to detect "
        "sophisticated cyber threats such as account takeovers, credential theft, bot attacks, VPN "
        "abuse, and coordinated fraudulent activities. To establish a robust security baseline, the "
        "National Institute of Standards and Technology (NIST) has highlighted the significance of "
        "behavioral biometrics [7], emphasizing the continuous capture and evaluation of keystroke "
        "dynamics, typing patterns, and interactive telemetry to verify identity implicitly."
    )
    lit_p2 = (
        "Machine Learning (ML) has emerged as an effective solution for fraud detection in banking "
        "systems. Various supervised learning algorithms, including Decision Trees, Random Forests, "
        "XGBoost, and LightGBM, have been widely used to analyze user behavior and classify "
        "transactions or login attempts as legitimate or fraudulent. The LightGBM framework proposed by "
        "Ke et al. [1] represents a highly efficient implementation that utilizes gradient-based one-side "
        "sampling and exclusive feature bundling to perform rapid classification on massive datasets "
        "with high accuracy. However, supervised models alone may struggle to identify previously "
        "unseen attack patterns or zero-day threats."
    )
    lit_p3 = (
        "To address this limitation, anomaly detection techniques have been introduced into fraud "
        "detection systems. Algorithms such as Isolation Forest, One-Class SVM, and Autoencoders "
        "can identify unusual activities that significantly differ from normal user behavior. These "
        "methods are particularly useful for detecting suspicious login attempts, abnormal device "
        "usage, and unexpected network activities. Combining supervised learning with anomaly detection "
        "improves the overall effectiveness of security systems."
    )
    lit_p4 = (
        "Recent research has also highlighted the importance of Graph Intelligence in cybersecurity "
        "and fraud detection. Graph databases such as Neo4j [4] enable organizations to analyze "
        "relationships between users, devices, IP addresses, and transactions [8]. Kipf and Welling "
        "introduced Graph Convolutional Networks (GCN) [5] to perform semi-supervised classification "
        "on graph structures, and Hamilton et al. developed GraphSAGE [6] to address scalability "
        "by learning aggregator functions that generalize to unseen nodes, allowing graph neural network "
        "embeddings to be computed dynamically in real-time streaming environments."
    )
    lit_p5 = (
        "Another important advancement in AI-driven security is Explainable Artificial Intelligence "
        "(XAI). Techniques such as SHAP [2] and TreeSHAP [3] provide transparent explanations for "
        "model predictions by identifying the factors that contribute to risk scores, which assists "
        "security analysts and auditors in understanding automated fraud decisions."
    )
    lit_p6 = (
        "Transitioning hybrid engines from experimental settings to production environments requires "
        "structured lifecycle management. Kreuzberger et al. defined the architecture for Machine Learning "
        "Operations (MLOps) [9], detailing automated pipelines to prevent model decay over time, while "
        "the Amazon Web Services (AWS) Architecture Center [10] provides designs for deploying "
        "decoupled microservices and secure object storage (such as AWS S3)."
    )
    story.append(Paragraph(lit_p1, style_body))
    story.append(Paragraph(lit_p2, style_body))
    story.append(Paragraph(lit_p3, style_body))
    story.append(Paragraph(lit_p4, style_body))
    story.append(Paragraph(lit_p5, style_body))
    story.append(Paragraph(lit_p6, style_body))
    story.append(PageBreak())

    # -------------------------------------------------------------
    # CHAPTER 3: PROBLEM STATEMENT AND OBJECTIVES (Page 4)
    # -------------------------------------------------------------
    story.append(PageTracker("CHAPTER 3: PROBLEM STATEMENT AND OBJECTIVES", page_dict))
    story.append(Paragraph("CHAPTER 3: PROBLEM STATEMENT AND OBJECTIVES", style_h1))
    story.append(Paragraph("3.1 Problem Statement", style_h2))
    prob_p1 = (
        "The increasing adoption of online banking and digital financial services has made cybersecurity "
        "a critical concern for financial institutions. Traditional authentication mechanisms such as "
        "usernames, passwords, and One-Time Passwords (OTPs) are widely used to verify user "
        "identity. Although these methods provide basic protection, they are often vulnerable to phishing "
        "attacks, credential theft, account takeovers, and other sophisticated cyber threats. As a result, "
        "unauthorized users may gain access to sensitive financial information, leading to financial "
        "losses and security breaches."
    )
    prob_p2 = (
        "Another major challenge is that conventional authentication systems primarily focus on "
        "validating user credentials and do not analyze behavioral patterns, device trust, network "
        "reputation, or hidden relationships between users and devices. Fraudulent activities such as "
        "VPN abuse, bot attacks, device sharing, and coordinated account compromises can therefore "
        "remain undetected. Rule-based security systems also struggle to identify new and evolving "
        "attack patterns, reducing their effectiveness in modern banking environments."
    )
    prob_p3 = (
        "To address these limitations, there is a need for an intelligent security framework that can "
        "continuously monitor user behavior, detect anomalies, analyze relationships among entities, "
        "and provide real-time risk assessment. Such a system should not only improve fraud detection "
        "accuracy but also maintain a seamless user experience without introducing significant delays "
        "during authentication."
    )
    prob_p4 = (
        "The proposed GraphShield system combines Machine Learning, Anomaly Detection, Graph "
        "Intelligence, and Explainable Artificial Intelligence (XAI) to create a comprehensive fraud "
        "detection and authentication platform. By analyzing behavioral, device, network, and relational "
        "data, the system can accurately identify suspicious activities, detect hidden fraud patterns, and "
        "provide transparent explanations for risk predictions. This approach enhances banking security "
        "while ensuring fast and reliable user authentication."
    )
    story.append(Paragraph(prob_p1, style_body))
    story.append(Paragraph(prob_p2, style_body))
    story.append(Paragraph(prob_p3, style_body))
    story.append(Paragraph(prob_p4, style_body))
    
    story.append(Paragraph("3.2 Objectives", style_h2))
    obj_intro = (
        "The primary objective of GraphShield is to develop an intelligent fraud detection and "
        "authentication system that enhances banking security using advanced Artificial Intelligence "
        "and Graph Analytics technologies."
    )
    story.append(Paragraph(obj_intro, style_body))
    
    objectives = [
        "To develop a secure and scalable banking authentication framework.",
        "To analyze user behavioral patterns and login activities for fraud detection.",
        "To implement Machine Learning models for identifying suspicious login attempts.",
        "To utilize Isolation Forest-based anomaly detection for detecting unusual user behavior.",
        "To integrate Neo4j Graph Intelligence for analyzing relationships between users, devices, and IP addresses.",
        "To identify coordinated fraud activities, device sharing, and account takeover attempts.",
        "To generate risk scores based on machine learning and graph-based analysis.",
        "To provide explainable fraud predictions using TreeSHAP explainability techniques.",
        "To store authentication logs, audit records, and risk analysis results securely.",
        "To reduce false positives while improving fraud detection accuracy.",
        "To maintain low-latency authentication without affecting user experience.",
        "To provide administrators with dashboards, alerts, and security insights for proactive threat monitoring."
    ]
    for obj in objectives:
        story.append(Paragraph(f"• {obj}", style_bullet))
    story.append(PageBreak())

    # -------------------------------------------------------------
    # CHAPTER 4: SOLUTION METHODOLOGY (Page 6)
    # -------------------------------------------------------------
    story.append(PageTracker("CHAPTER 4: SOLUTION METHODOLOGY", page_dict))
    story.append(Paragraph("CHAPTER 4: SOLUTION METHODOLOGY", style_h1))
    method_intro = (
        "The GraphShield system is designed to enhance banking security by combining Machine "
        "Learning, Anomaly Detection, Graph Intelligence, and Explainable Artificial Intelligence "
        "(XAI). The proposed system evaluates user login activities by analyzing behavioral patterns, "
        "device information, network characteristics, and historical session data. The methodology "
        "follows a structured workflow that begins with user authentication and continues with "
        "advanced fraud analysis and risk assessment."
    )
    story.append(Paragraph(method_intro, style_body))
    
    story.append(Paragraph("4.1 System Workflow", style_h2))
    story.append(Paragraph("The proposed system follows the workflow shown below:", style_body))
    
    # Insert Workflow flowchart image
    if os.path.exists(workflow_img_path):
        # Original size: 1024x439, aspect ratio = 2.33
        story.append(Image(workflow_img_path, width=6.5*inch, height=2.8*inch))
    else:
        story.append(Paragraph("[Missing Image: workflow_flowchart.png]", style_body))
        
    story.append(PageBreak())
    
    # Repeat subheading 4.1 for the workflow text as in the original PDF
    story.append(Paragraph("4.1 System Workflow", style_h2))
    wf_p = (
        "The proposed system follows a decoupled dual-flow pipeline. The ingestion flow captures "
        "incoming biometrics and client parameters, immediately backing them up to S3 and returning "
        "an allow confirmation. The parallel evaluation flow extracts historical features, scores "
        "tabular data via LightGBM and Isolation Forest, logs relational edges in Neo4j, writes "
        "verdicts and TreeSHAP calculations to S3 and MongoDB, and updates operator dashboards."
    )
    story.append(Paragraph(wf_p, style_body))

    story.append(Paragraph("4.2 Dual-Flow API and Async Worker Setup", style_h2))
    sec_4_2 = (
        "The orchestrator endpoint /api/security/check-login is optimized for zero user latency. "
        "Upon receiving a transaction, it spawns a session identifier and saves the payload. "
        "It then spawns a daemon thread to run feature engineering and parallel model prediction, "
        "allowing the main HTTP thread to return an immediate success response to the client bank."
    )
    story.append(Paragraph(sec_4_2, style_body))

    story.append(Paragraph("4.3 S3 Simulated Object Store Layout", style_h2))
    sec_4_3 = (
        "To secure immutable audit traces, all outputs are archived in a structured mock S3 storage hierarchy. "
        "Each session creates a unique root directory (SESSION_YYYYMMDD_XYZ/) containing: "
        "/raw/ (telemetry payload), /extracted/ (computed feature vectors), /graph/ (adjacency Cypher "
        "matrices), and /alerts/ (verdict JSON and TreeSHAP matrix)."
    )
    story.append(Paragraph(sec_4_3, style_body))

    story.append(Paragraph("4.4 Dynamic Feature Engineering Module", style_h2))
    sec_4_4 = (
        "When the async worker begins evaluation, it queries the MongoDB transaction history to fetch the "
        "last 10 sessions. It computes key features on the fly, including: failed_attempts (count of recent blocks), "
        "ip_change_count (unique IP configurations), request_interval (delay duration to detect bot script), "
        "typing_speed (average keystroke characters per second), and is_new_device."
    )
    story.append(Paragraph(sec_4_4, style_body))

    story.append(Paragraph("4.5 LightGBM Supervised Risk Classification", style_h2))
    sec_4_5 = (
        "The tabular ML classifier is based on LightGBM. The model predicts the probability "
        "of fraudulent activity (P_lgbm) by analyzing tabular behavioral vectors. It is highly optimized "
        "for swift decision-tree traversal, completing inference in microseconds."
    )
    story.append(Paragraph(sec_4_5, style_body))

    story.append(Paragraph("4.6 Isolation Forest Unsupervised Anomaly Scoring", style_h2))
    sec_4_6 = (
        "An unsupervised Isolation Forest anomaly model is loaded in parallel. It detects deviations "
        "from normal user behavior by partitioning outliers. It evaluates whether the session parameters "
        "represent a structural outlier, returning a binary anomaly score (S_anomaly)."
    )
    story.append(Paragraph(sec_4_6, style_body))

    story.append(Paragraph("4.7 Neo4j Graph Relational Mapping", style_h2))
    sec_4_7 = (
        "The graph database layer connects via Bolt protocol. It injects user-device-IP relationships and "
        "queries traversal paths. It calculates relational metrics: device reuse (users per device), "
        "IP rotation (IPs per device), and cross-bank device footprints to generate a graph risk score (S_graph)."
    )
    story.append(Paragraph(sec_4_7, style_body))

    story.append(Paragraph("4.8 Parallel Inference & Decision Orchestration", style_h2))
    sec_4_8 = (
        "The decision engine executes ML scoring and Graph DB queries concurrently using a ThreadPoolExecutor. "
        "It aggregates the results using a weighted formula: S_final = 0.5 * S_ml + 0.5 * S_graph (where "
        "S_ml = 0.7 * P_lgbm + 0.3 * S_anomaly). If S_final >= 0.5, a BLOCK action is registered."
    )
    story.append(Paragraph(sec_4_8, style_body))

    story.append(Paragraph("4.9 TreeSHAP Local Attributions", style_h2))
    sec_4_9 = (
        "To achieve explainability, the background thread runs TreeSHAP to decompose tree output weights into "
        "percentage contributions. These normalized values are saved directly to the database, enabling "
        "operators to verify the reason behind each blocking decision."
    )
    story.append(Paragraph(sec_4_9, style_body))

    story.append(Paragraph("4.10 Database Persistence & Storage", style_h2))
    sec_4_10 = (
        "Operational parameters, credentials, active subscriptions, and risk events are stored in MongoDB. "
        "To ensure high availability in Neo4j-offline dev environments, a mock graph fallback "
        "automatically writes relationship nodes and edges directly to MongoDB collections."
    )
    story.append(Paragraph(sec_4_10, style_body))

    story.append(Paragraph("4.11 UI Portals and Dashboard Module", style_h2))
    sec_4_11 = (
        "Developed portals using Flutter Web for three main roles: Users (monitor personal log history), "
        "Banks (onboard pending accounts and check subscriptions), and Admins (monitor global threat logs, "
        "inspect active graph networks, and review TreeSHAP percentage attributions)."
    )
    story.append(Paragraph(sec_4_11, style_body))
    story.append(PageBreak())

    # -------------------------------------------------------------
    # CHAPTER 5: IMPLEMENTATION (Page 9)
    # -------------------------------------------------------------
    story.append(PageTracker("CHAPTER 5: IMPLEMENTATION", page_dict))
    story.append(Paragraph("CHAPTER 5: IMPLEMENTATION", style_h1))
    impl_intro = (
        "The GraphShield system is implemented using Machine Learning, Graph Analytics, "
        "Explainable Artificial Intelligence (XAI), and modern web technologies to provide intelligent "
        "fraud detection and secure banking authentication. The system is designed to analyze user login "
        "behavior, detect anomalies, identify hidden fraud patterns, and generate risk assessments in "
        "real time. Each module performs a specific function to ensure secure and efficient "
        "authentication."
    )
    story.append(Paragraph(impl_intro, style_body))
    
    impl_modules = [
        ("5.1 User Authentication", "The implementation process begins when a user enters login credentials through the banking application. The system validates the credentials using secure authentication mechanisms and grants access only to authorized users. After successful authentication, additional security analysis is triggered to evaluate the legitimacy of the login session."),
        ("5.2 Data Collection and Session Monitoring", "The system collects behavioral, device, and network information during each login session. Data such as typing speed, keystroke dynamics, browser fingerprints, device identifiers, IP addresses, VPN status, and network reputation are captured and stored for further analysis. Historical login records are also retrieved to provide contextual information."),
        ("5.3 Feature Engineering", "The collected raw data is processed and transformed into meaningful features. Behavioral indicators, device trust scores, login frequency metrics, and network-related attributes are generated to create a structured dataset. These engineered features improve the effectiveness of fraud detection models."),
        ("5.4 Machine Learning-Based Fraud Detection", "The processed features are analyzed using a LightGBM machine learning model trained on historical banking session data. The model predicts the probability of fraudulent activity by identifying patterns associated with suspicious login attempts and account takeover attacks."),
        ("5.5 Anomaly Detection", "The system employs the Isolation Forest algorithm to identify unusual user behavior. This module detects anomalies by comparing current activities with normal user patterns and flags suspicious events that may indicate emerging fraud attempts or previously unseen threats."),
        ("5.6 Graph Intelligence Analysis", "Neo4j Graph Database is implemented to analyze relationships between users, devices, IP addresses, and login sessions. The graph layer identifies device sharing, IP rotation, coordinated attacks, and hidden fraud networks by examining connections among different entities."),
        ("5.7 Hybrid Risk Scoring", "The outputs from the LightGBM classifier, Isolation Forest anomaly detector, and graph intelligence engine are combined to generate a final risk score. This hybrid scoring mechanism provides a more accurate assessment of login risk by considering multiple fraud indicators simultaneously."),
        ("5.8 Explainable AI Integration", "TreeSHAP explainability techniques are integrated into the system to provide transparent explanations for risk predictions. The module highlights the factors that contributed most significantly to a risk score, enabling administrators and security analysts to understand fraud detection decisions."),
        ("5.9 Database Storage", "MongoDB is used to securely store authentication logs, session history, risk scores, graph relationships, fraud alerts, and audit reports. The database supports efficient data retrieval, historical analysis, and compliance reporting while ensuring scalability and reliability for large-scale banking applications.")
    ]
    for title, desc in impl_modules:
        story.append(Paragraph(title, style_h2))
        story.append(Paragraph(desc, style_body))
    
    # 5.10 Core Decision Engine Implementation code snippet
    story.append(Paragraph("5.10 Core Decision Engine Implementation", style_h2))
    story.append(Paragraph(
        "Below is a code snippet from the core Decision Engine orchestration class, showcasing "
        "the asynchronous telemetry logging, parallel execution of tabular and graph models, "
        "and dynamic rule-based scoring:",
        style_body
    ))
    
    code_snippet = (
        "class DecisionEngine:\n"
        "    def evaluate_login(self, user_id, device_id, ip_address, bank_id, ...):\n"
        "        # 1. Compute dynamic behavioral features\n"
        "        features = compute_features(user_id, device_id, ip_address, bank_id)\n\n"
        "        # 2. Parallel ML and Graph score execution\n"
        "        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:\n"
        "            ml_future = executor.submit(lambda: ml_engine.compute_ml_score(features))\n"
        "            graph_future = executor.submit(lambda: graph_db.calc_graph_score(device_id))\n\n"
        "            ml_score = ml_future.result()\n"
        "            graph_score = graph_future.result()\n\n"
        "        # 3. Hybrid decision scoring and risk assessment\n"
        "        final_score = 0.5 * ml_score + 0.5 * graph_score\n"
        "        if final_score >= 0.5:\n"
        "            decision, risk_level = 'BLOCK', 'HIGH'\n"
        "        else:\n"
        "            decision, risk_level = 'ALLOW', 'LOW'\n\n"
        "        # 4. Persistence and storage\n"
        "        db.risk_events.insert_one({\"session_id\": session_id, \"decision\": decision, ...})\n"
        "        return decision"
    )
    
    style_code = ParagraphStyle(
        name='Code_Style',
        fontName='Courier',
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor("#1F2937"),
        spaceAfter=10,
        leftIndent=15
    )
    story.append(Preformatted(code_snippet, style_code))
    story.append(PageBreak())

    # -------------------------------------------------------------
    # CHAPTER 6: PRESENTATION OF RESULTS (Page 11)
    # -------------------------------------------------------------
    story.append(PageTracker("CHAPTER 6: PRESENTATION OF RESULTS", page_dict))
    story.append(Paragraph("CHAPTER 6: PRESENTATION OF RESULTS", style_h1))
    res_intro = (
        "The GraphShield system was successfully developed and tested using banking session records "
        "containing behavioral, device, and network-related features. The system was able to "
        "authenticate users, analyze login activities, detect anomalies, identify suspicious relationships "
        "through graph analytics, and generate risk scores with explainable insights. The obtained "
        "results demonstrate that the proposed framework improves fraud detection accuracy while "
        "maintaining low authentication latency."
    )
    story.append(Paragraph(res_intro, style_body))

    res_sections = [
        ("6.1 User Authentication Performance", "The authentication module successfully validated user credentials and provided immediate login approval for legitimate users. The dual-flow architecture ensured that authentication decisions were delivered without noticeable delays while advanced fraud analysis continued in the background.\nResult:\nThe system provided secure and low-latency authentication, improving user experience without compromising security."),
        ("6.2 Machine Learning-Based Fraud Detection", "The LightGBM classifier analyzed user behavioral patterns, device information, and network characteristics to identify suspicious login activities. The model effectively differentiated between legitimate and fraudulent sessions.\nResult:\nThe machine learning model achieved high fraud detection accuracy and successfully identified potential account takeover attempts."),
        ("6.3 Anomaly Detection Performance", "The Isolation Forest algorithm evaluated login activities and detected deviations from normal user behavior. Unusual login patterns, unexpected device usage, and abnormal access attempts were successfully identified.\nResult:\nThe anomaly detection module improved the system's ability to recognize previously unseen threats and emerging attack patterns."),
        ("6.4 Graph Intelligence Analysis", "Neo4j Graph Analytics was used to examine relationships among users, devices, and IP addresses. The system successfully detected device-sharing behavior, IP rotation patterns, and interconnected fraud activities.\nResult:\nGraph analysis revealed hidden fraud networks and relationship-based threats that were not easily detectable through traditional methods."),
        ("6.5 Explainable AI Results", "TreeSHAP explainability techniques provided detailed explanations for generated risk scores. The system identified the most influential features contributing to each fraud prediction.\nResult:\nSecurity analysts were able to understand and verify fraud detection decisions, improving transparency and trust in the system."),
        ("6.6 Risk Score Generation", "The hybrid scoring engine combined machine learning predictions, anomaly detection results, and graph intelligence insights to generate a comprehensive risk score for each login session.\nResult:\nThe final risk scores accurately reflected the threat level associated with user activities and supported effective decision-making."),
        ("6.7 Overall System Performance", "The integrated GraphShield framework successfully detected fraudulent activities while maintaining fast authentication performance. The system demonstrated the ability to identify account takeover attempts, suspicious device usage, VPN abuse, coordinated bot activity, and hidden fraud relationships.")
    ]
    for title, desc in res_sections:
        story.append(Paragraph(title, style_h2))
        story.append(Paragraph(desc.replace("\n", "<br/>"), style_body))

    story.append(PageBreak())

    # -------------------------------------------------------------
    # 6.8 ADMIN DASHBOARD INTERFACE (Page 13)
    # -------------------------------------------------------------
    story.append(Paragraph("6.8 Admin Dashboard Interface", style_h2))
    story.append(Paragraph(
        "The global threat administration panel provides real-time transaction feeds, active Graph "
        "database connections, and TreeSHAP risk analytics. System administrators use this panel to "
        "monitor threat thresholds and approve bank configurations:",
        style_body
    ))
    if os.path.exists(admin_img_path):
        story.append(Image(admin_img_path, width=5.5*inch, height=5.5*inch))
    else:
        story.append(Paragraph("[Missing Image: admin_dashboard.jpg]", style_body))
        
    story.append(PageBreak())

    # -------------------------------------------------------------
    # 6.9 USER PORTAL AND AUTHENTICATION INTERFACE (Page 14)
    # -------------------------------------------------------------
    story.append(Paragraph("6.9 User Portal and Authentication Interface", style_h2))
    story.append(Paragraph(
        "The user-facing access management panel details specific login histories, device trusted indices, "
        "and multi-factor authentication controls, providing zero-trust security confirmation:",
        style_body
    ))
    
    # We place user_panel and login_panel stacked on this page
    if os.path.exists(user_img_path):
        story.append(Image(user_img_path, width=3.6*inch, height=3.6*inch))
    else:
        story.append(Paragraph("[Missing Image: user_panel.jpg]", style_body))
        
    story.append(Spacer(1, 10))
    
    if os.path.exists(login_img_path):
        story.append(Image(login_img_path, width=3.6*inch, height=3.6*inch))
    else:
        story.append(Paragraph("[Missing Image: login_panel.jpg]", style_body))

    story.append(PageBreak())

    # -------------------------------------------------------------
    # Summary of Results (Table)
    # -------------------------------------------------------------
    story.append(Paragraph("Summary of Results", style_h2))
    
    table_data = [
        ["User Authentication Module", "Provided secure and low-latency login verification"],
        ["Data Collection", "Captured behavioral, device, and network information accurately"],
        ["Feature Engineering", "Generated meaningful indicators for fraud analysis"],
        ["LightGBM Classifier", "Detected fraudulent login attempts with high accuracy"],
        ["Isolation Forest", "Identified abnormal user behavior and suspicious activities"],
        ["Neo4j Graph Analytics", "Detected hidden fraud networks, device sharing, and IP rotation patterns"],
        ["TreeSHAP Explainability", "Generated transparent explanations for risk predictions"],
        ["MongoDB Storage", "Securely stored session logs, risk scores, and audit reports"]
    ]
    
    # Prefix header
    table_data.insert(0, ["Module", "Result / Output"])
    
    t = Table(table_data, colWidths=[2.5*inch, 4.5*inch])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (1,0), colors.HexColor("#1E3A8A")),
        ('TEXTCOLOR', (0,0), (1,0), colors.white),
        ('FONTNAME', (0,0), (1,0), 'Times-Bold'),
        ('FONTSIZE', (0,0), (1,0), 11),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#9CA3AF")),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.HexColor("#F9FAFB"), colors.white]),
        ('FONTNAME', (0,1), (-1,-1), 'Times-Roman'),
        ('FONTSIZE', (0,1), (-1,-1), 10),
    ]))
    story.append(t)
    story.append(PageBreak())

    # -------------------------------------------------------------
    # CHAPTER 7: PERFORMANCE ANALYSIS (Page 16)
    # -------------------------------------------------------------
    story.append(PageTracker("CHAPTER 7: PERFORMANCE ANALYSIS", page_dict))
    story.append(Paragraph("CHAPTER 7: PERFORMANCE ANALYSIS", style_h1))
    perf_intro = (
        "The performance of the GraphShield system was analyzed based on various parameters such "
        "as fraud detection accuracy, anomaly detection capability, authentication latency, graph "
        "intelligence analysis, explainability, and overall system efficiency. The system was tested using "
        "banking session records containing behavioral, device, and network-related features. The "
        "results demonstrate that the proposed framework provides accurate fraud detection while "
        "maintaining fast and secure authentication."
    )
    story.append(Paragraph(perf_intro, style_body))

    perf_sections = [
        ("7.1 Authentication Performance", "The authentication module successfully verified user credentials and provided immediate access to legitimate users. The dual-flow architecture ensured that advanced fraud analysis was performed in the background without affecting the login experience.\nAnalysis:\nThe system maintained low authentication latency while ensuring secure access control for banking users."),
        ("7.2 Machine Learning Performance", "The LightGBM classifier analyzed user behavior and login patterns to identify fraudulent activities. The model was trained using historical banking session data and achieved high prediction accuracy.\nAnalysis:\nThe machine learning model effectively distinguished between legitimate and fraudulent login attempts, reducing security risks."),
        ("7.3 Anomaly Detection Performance", "The Isolation Forest algorithm evaluated user activities and detected deviations from normal behavioral patterns. Suspicious login attempts and unusual activities were successfully identified.\nAnalysis:\nThe anomaly detection module improved the system's ability to detect emerging threats and previously unseen attack patterns."),
        ("7.4 Graph Intelligence Performance", "Neo4j Graph Analytics examined relationships among users, devices, IP addresses, and login sessions. Hidden fraud networks and suspicious connections were successfully identified.\nAnalysis:\nGraph-based analysis enhanced fraud detection by uncovering relationship-based threats that traditional methods often miss.")
    ]
    for title, desc in perf_sections:
        story.append(Paragraph(title, style_h2))
        story.append(Paragraph(desc.replace("\n", "<br/>"), style_body))
        
    story.append(Paragraph("7.5 Overall System Performance", style_h2))
    overall_p = "The major performance improvements achieved by the GraphShield system include:"
    story.append(Paragraph(overall_p, style_body))
    
    improvements = [
        "Accurate detection of fraudulent login attempts using Machine Learning techniques.",
        "Effective identification of abnormal user behavior through Isolation Forest anomaly detection.",
        "Detection of hidden fraud networks, device sharing, and IP rotation patterns using Neo4j Graph Analytics.",
        "Secure storage of authentication logs, risk scores, and audit reports using MongoDB.",
        "Real-time fraud monitoring and alert generation for suspicious activities.",
        "Low-latency authentication with high security, achieving 94.43% Accuracy, 89.70% Precision, 91.86% Recall, and 90.77% F1-Score."
    ]
    for imp in improvements:
        story.append(Paragraph(f"• {imp}", style_bullet))
        
    story.append(PageBreak())

    # -------------------------------------------------------------
    # 7.6 PERFORMANCE COMPARISON TABLES (Page 17)
    # -------------------------------------------------------------
    story.append(Paragraph("7.6 Performance Comparison Tables", style_h2))
    story.append(Paragraph("Performance Comparison", style_body))
    
    table_data_comp1 = [
        ["Parameter", "Traditional Banking Security", "GraphShield System"],
        ["Fraud Detection Accuracy", "75%", "94.43%"],
        ["Authentication Security", "Basic Credential Verification", "AI-Powered Multi-Layer"],
        ["Anomaly Detection", "Limited", "Advanced Isolation"],
        ["Hidden Fraud Detection", "Not Supported", "Neo4j Graph Analytics"],
        ["Explainability", "Not Available", "TreeSHAP-Based"],
        ["Real-Time Monitoring", "Limited", "Continuous Risk Monitoring"],
        ["Risk Assessment", "Rule-Based", "Hybrid ML + Graph Intelligence"]
    ]
    
    t_comp1 = Table(table_data_comp1, colWidths=[2.2*inch, 2.3*inch, 2.5*inch])
    t_comp1.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#1E3A8A")),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,0), 'Times-Bold'),
        ('FONTSIZE', (0,0), (-1,0), 10),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#9CA3AF")),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.HexColor("#F9FAFB"), colors.white]),
        ('FONTNAME', (0,1), (-1,-1), 'Times-Roman'),
        ('FONTSIZE', (0,1), (-1,-1), 9),
    ]))
    story.append(t_comp1)
    story.append(Spacer(1, 15))
    
    story.append(Paragraph("Performance Metrics Comparison", style_body))
    table_data_comp2 = [
        ["Metric", "Traditional System", "GraphShield System"],
        ["Accuracy (%)", "75", "94.43"],
        ["Precision (%)", "70", "89.70"],
        ["Recall (%)", "72", "91.86"],
        ["F1-Score (%)", "71", "90.77"]
    ]
    t_comp2 = Table(table_data_comp2, colWidths=[2.2*inch, 2.3*inch, 2.5*inch])
    t_comp2.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#10B981")),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,0), 'Times-Bold'),
        ('FONTSIZE', (0,0), (-1,0), 10),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#9CA3AF")),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.HexColor("#F9FAFB"), colors.white]),
        ('FONTNAME', (0,1), (-1,-1), 'Times-Roman'),
        ('FONTSIZE', (0,1), (-1,-1), 9),
    ]))
    story.append(t_comp2)
    story.append(PageBreak())

    # -------------------------------------------------------------
    # 7.7 PERFORMANCE METRICS COMPARISON CHART (Page 18)
    # -------------------------------------------------------------
    story.append(Paragraph("7.7 Performance Metrics Comparison Chart", style_h2))
    story.append(Paragraph(
        "The bar chart below represents the relative comparison of Accuracy, Precision, Recall, and F1-Score "
        "between traditional credential-based systems and the multi-layered GraphShield platform:",
        style_body
    ))
    if os.path.exists(perf_img_path):
        story.append(Image(perf_img_path, width=5.5*inch, height=5.5*inch))
    else:
        story.append(Paragraph("[Missing Image: performance_chart.png]", style_body))
        
    story.append(PageBreak())

    # -------------------------------------------------------------
    # CHAPTER 8: APPLICATIONS (Page 20)
    # -------------------------------------------------------------
    story.append(PageTracker("CHAPTER 8: APPLICATIONS", page_dict))
    story.append(Paragraph("CHAPTER 8: APPLICATIONS", style_h1))
    app_intro = (
        "The GraphShield system has a wide range of applications in the banking and financial sector. "
        "By combining Machine Learning, Anomaly Detection, Graph Intelligence, and Explainable AI, "
        "the system enhances security, reduces fraud risks, and improves user trust. The major "
        "applications of the proposed system are as follows:"
    )
    story.append(Paragraph(app_intro, style_body))
    
    apps = [
        ("8.1 Online Banking Security", "The system can be used to secure online banking platforms by detecting fraudulent login attempts, account takeover attacks, and unauthorized access in real time."),
        ("8.2 Mobile Banking Applications", "GraphShield can be integrated into mobile banking applications to monitor user behavior, analyze device trust, and provide secure authentication for mobile transactions."),
        ("8.3 Fraud Detection in Financial Institutions", "Banks and financial organizations can use the system to identify suspicious activities, detect fraud networks, and prevent financial losses caused by cybercriminals."),
        ("8.4 Credit Card and Digital Payment Security", "The system can analyze transaction patterns and user behavior to detect fraudulent card usage, unauthorized payments, and suspicious financial activities."),
        ("8.5 Account Takeover Prevention", "GraphShield helps identify abnormal login behavior, unusual device usage, and credential misuse, reducing the risk of account compromise and identity theft."),
        ("8.6 Cybersecurity Monitoring", "Organizations can use the system for continuous monitoring of authentication events, risk assessment, and security incident detection across digital platforms."),
        ("8.7 Regulatory Compliance and Auditing", "The system maintains detailed authentication logs, risk assessments, and audit reports, helping financial institutions comply with security regulations and auditing requirements."),
        ("8.8 Enterprise Access Management", "The proposed framework can be adapted for enterprise applications to secure employee accounts, monitor access behavior, and prevent unauthorized system access.")
    ]
    for title, desc in apps:
        story.append(Paragraph(title, style_h2))
        story.append(Paragraph(desc, style_body))
    story.append(PageBreak())

    # -------------------------------------------------------------
    # CHAPTER 9: FUTURE SCOPE (Page 22)
    # -------------------------------------------------------------
    story.append(PageTracker("CHAPTER 9: FUTURE SCOPE", page_dict))
    story.append(Paragraph("CHAPTER 9: FUTURE SCOPE", style_h1))
    fs_intro = (
        "The GraphShield system provides an intelligent and secure solution for fraud detection and "
        "banking authentication. However, there are several opportunities to enhance the system further "
        "by integrating advanced technologies and additional security features. These improvements "
        "will increase the system's accuracy, scalability, and adaptability to evolving cyber threats."
    )
    story.append(Paragraph(fs_intro, style_body))
    
    scopes = [
        ("9.1 Advanced Graph Analytics", "Future versions of the system can incorporate Neo4j Graph Data Science algorithms to perform deeper relationship analysis and identify complex fraud networks with greater accuracy."),
        ("9.2 Automated Multi-Factor Authentication (MFA)", "The system can be enhanced to automatically trigger additional authentication methods such as OTP verification, biometric authentication, or security questions when high-risk activities are detected."),
        ("9.3 Continuous Behavioral Authentication", "Instead of analyzing users only during login, future implementations can continuously monitor user behavior throughout the banking session to detect suspicious activities in real time."),
        ("9.4 Cloud-Based Deployment", "The GraphShield platform can be deployed on cloud infrastructure to improve scalability, availability, and performance while supporting millions of banking transactions and authentication requests."),
        ("9.5 Real-Time Threat Intelligence Integration", "The system can be integrated with external cybersecurity threat intelligence feeds to identify newly emerging attack patterns, malicious IP addresses, and compromised devices."),
        ("9.6 Deep Learning-Based Fraud Detection", "Future versions can utilize advanced deep learning models such as LSTM networks, Transformers, and Graph Neural Networks (GNNs) to improve fraud detection accuracy and predictive capabilities."),
        ("9.7 Cross-Bank Fraud Detection Network", "The framework can be extended to support collaboration among multiple financial institutions, enabling the sharing of anonymized fraud intelligence to detect large-scale coordinated attacks."),
        ("9.8 Mobile and Biometric Security Integration", "Future enhancements can integrate facial recognition, fingerprint authentication, and mobile device biometrics to provide stronger identity verification and improve user security."),
        ("9.9 AI-Powered Fraud Prediction", "Future versions of GraphShield can incorporate predictive analytics to identify potential fraud risks before they occur. By analyzing historical user behavior and transaction patterns, the system can proactively detect high-risk accounts and prevent fraudulent activities at an early stage."),
        ("9.10 Blockchain Integration for Secure Auditing", "The system can be integrated with blockchain technology to create tamper-proof audit logs and transaction records. This will enhance transparency, improve data integrity, and provide a secure mechanism for tracking authentication events and fraud investigations.")
    ]
    for title, desc in scopes:
        story.append(Paragraph(title, style_h2))
        story.append(Paragraph(desc, style_body))
    story.append(PageBreak())

    # -------------------------------------------------------------
    # CHAPTER 10: CONCLUSION (Page 24)
    # -------------------------------------------------------------
    story.append(PageTracker("CHAPTER 10: CONCLUSION", page_dict))
    story.append(Paragraph("CHAPTER 10: CONCLUSION", style_h1))
    conclusion_p1 = (
        "The GraphShield system is an intelligent and efficient solution developed to enhance banking "
        "security through advanced fraud detection and authentication mechanisms. The system "
        "combines Machine Learning, Anomaly Detection, Graph Intelligence, and Explainable "
        "Artificial Intelligence (XAI) to provide a comprehensive approach for identifying suspicious "
        "activities and preventing unauthorized access. By analyzing behavioral patterns, device "
        "information, network attributes, and relationship-based fraud indicators, the system offers "
        "accurate and reliable risk assessment."
    )
    conclusion_p2 = (
        "The proposed framework successfully integrates LightGBM, Isolation Forest, Neo4j Graph "
        "Analytics, TreeSHAP Explainability, MongoDB, and modern web technologies to create a "
        "scalable fraud detection platform. The hybrid risk scoring mechanism improves detection "
        "accuracy while maintaining low authentication latency and a seamless user experience. The "
        "explainability component further enhances transparency by providing clear insights into the "
        "factors influencing fraud predictions."
    )
    conclusion_p3 = (
        "Overall, GraphShield significantly improves traditional banking security systems by enabling "
        "real-time fraud detection, intelligent risk analysis, and proactive threat monitoring. The system "
        "achieved high performance with an accuracy of 94.43%, demonstrating its effectiveness in "
        "detecting account takeover attempts, suspicious device usage, VPN abuse, and coordinated "
        "fraud activities. With future enhancements such as continuous behavioral authentication, cloud "
        "deployment, advanced graph analytics, and AI-powered fraud prediction, GraphShield has the "
        "potential to become a robust and scalable security solution for modern banking and financial "
        "institutions."
    )
    story.append(Paragraph(conclusion_p1, style_body))
    story.append(Paragraph(conclusion_p2, style_body))
    story.append(Paragraph(conclusion_p3, style_body))
    story.append(PageBreak())

    # -------------------------------------------------------------
    # REFERENCES (Page 25)
    # -------------------------------------------------------------
    story.append(PageTracker("REFERENCES", page_dict))
    story.append(Paragraph("REFERENCES", style_h1))
    
    refs = [
        "G. Ke, Q. Meng, T. Finley, T. Wang, W. Chen, W. Ma, Q. Ye, and T.-Y. Liu, \"LightGBM: A Highly Efficient Gradient Boosting Decision Tree,\" in Advances in Neural Information Processing Systems (NeurIPS), vol. 30, pp. 3146-3154, 2017. [Online]. Available: https://papers.nips.cc/paper/6907-lightgbm-a-highly-efficient-boosting-decision-tree",
        "S. M. Lundberg and S.-I. Lee, \"A Unified Approach to Interpreting Model Predictions,\" in Advances in Neural Information Processing Systems (NeurIPS), vol. 30, pp. 4765-4774, 2017. [Online]. Available: https://arxiv.org/abs/1705.07874",
        "S. M. Lundberg, G. G. Erion, and S.-I. Lee, \"Consistent Feature Attribution for Tree Ensembles,\" arXiv preprint arXiv:1706.06060, 2017. [Online]. Available: https://arxiv.org/abs/1706.06060",
        "Neo4j Inc., \"Neo4j Graph Database Platform,\" Neo4j Documentation, 2023. [Online]. Available: https://neo4j.com",
        "T. N. Kipf and M. Welling, \"Semi-Supervised Classification with Graph Convolutional Networks,\" in Proceedings of the International Conference on Learning Representations (ICLR), 2017. [Online]. Available: https://arxiv.org/abs/1609.02907",
        "W. Hamilton, Z. Ying, and J. Leskovec, \"Inductive Representation Learning on Large Graphs,\" in Advances in Neural Information Processing Systems (NeurIPS), vol. 30, pp. 1024-1034, 2017. [Online]. Available: https://arxiv.org/abs/1706.02216",
        "National Institute of Standards and Technology (NIST), \"Behavioral Biometrics,\" NIST Technical Report, 2021. [Online]. Available: https://www.nist.gov/topics/biometrics",
        "Neo4j Inc., \"Graph Analytics for Fraud Detection,\" Neo4j Use Cases, 2023. [Online]. Available: https://neo4j.com/use-cases/fraud-detection/",
        "D. Kreuzberger, N. Kuhl, and S. Hirschl, \"Machine Learning Operations (MLOps): Overview, Definition, and Architecture,\" IEEE Access, vol. 11, pp. 31866-31879, 2023. doi: 10.1109/ACCESS.2023.3262138.",
        "Amazon Web Services, \"AWS Architecture Center,\" AWS Documentation, 2023. [Online]. Available: https://aws.amazon.com/architecture/"
    ]

    for i, ref in enumerate(refs):
        ref_text = f"[{i+1}] {ref}"
        story.append(Paragraph(ref_text, style_ref))

    return story

def build_pdf():
    pdf_filename = "c:/security_banking_app/GraphShield_Security_Engine_Report.pdf"
    doc = SimpleDocTemplate(
        pdf_filename,
        pagesize=letter,
        leftMargin=inch*0.75,
        rightMargin=inch*0.75,
        topMargin=inch*0.8,
        bottomMargin=inch*0.8
    )

    styles = getSampleStyleSheet()
    
    # Times New Roman styles configured to requested font sizes:
    # Content heading: 16 (black), Content sub-heading: 14 (black), Body content: 12
    style_h1 = ParagraphStyle(
        name='Heading1_Custom',
        fontName='Times-Bold',
        fontSize=16,
        leading=20,
        textColor=colors.black,
        spaceAfter=14,
        keepWithNext=True
    )
    
    style_h2 = ParagraphStyle(
        name='Heading2_Custom',
        fontName='Times-Bold',
        fontSize=14,
        leading=18,
        textColor=colors.black,
        spaceBefore=10,
        spaceAfter=8,
        keepWithNext=True
    )

    style_body = ParagraphStyle(
        name='Body_Custom',
        fontName='Times-Roman',
        fontSize=12,
        leading=16,
        textColor=colors.HexColor("#111827"),
        spaceAfter=10
    )
    
    style_bullet = ParagraphStyle(
        name='Bullet_Custom',
        fontName='Times-Roman',
        fontSize=12,
        leading=16,
        textColor=colors.HexColor("#111827"),
        leftIndent=24,
        firstLineIndent=-12,
        spaceAfter=6
    )
    
    style_ref = ParagraphStyle(
        name='Ref_Custom',
        fontName='Times-Roman',
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#1F2937"),
        leftIndent=24,
        firstLineIndent=-24,
        spaceAfter=10
    )

    styles.add(style_h1)
    styles.add(style_h2)
    styles.add(style_body)
    styles.add(style_bullet)
    styles.add(style_ref)

    # PASS 1: Build the storyboard and layout to detect pages dynamically
    global CHAPTER_PAGES
    CHAPTER_PAGES = {}
    
    story_pass1 = build_story(styles, page_dict=CHAPTER_PAGES)
    doc.build(story_pass1, canvasmaker=NumberedCanvas)
    
    print("Pass 1 Complete. Recorded Chapter Page Mapping:")
    print(CHAPTER_PAGES)
    
    # PASS 2: Re-build using actual page numbers measured from Pass 1
    story_pass2 = build_story(styles, page_dict=CHAPTER_PAGES)
    doc.build(story_pass2, canvasmaker=NumberedCanvas)
    
    print("Pass 2 Complete. Final PDF compiled with correct page numbers in Index.")

if __name__ == '__main__':
    build_pdf()
