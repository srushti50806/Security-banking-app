import logging

try:
    from neo4j import GraphDatabase
except Exception:  # pragma: no cover - environment dependency fallback
    GraphDatabase = None

logger = logging.getLogger(__name__)


class GraphDB:
    def __init__(self, uri, user, password):
        if GraphDatabase is None:
            logger.warning("neo4j package not installed. Graph DB features are disabled.")
            self.driver = None
            return
        try:
            self.driver = GraphDatabase.driver(uri, auth=(user, password))
            self.driver.verify_connectivity()
            logger.info("Connected to Neo4j")
        except Exception as exc:
            logger.warning("Failed to connect to Neo4j database: %s. Falling back to MongoDB mock graph.", exc)
            try:
                if self.driver is not None:
                    self.driver.close()
            except Exception:
                pass
            self.driver = None

    def close(self):
        if self.driver is not None:
            self.driver.close()

    def log_activity(self, user_id, device_id, ip, bank_id):
        if self.driver is None:
            return self._log_activity_fallback(user_id, device_id, ip, bank_id)
        try:
            with self.driver.session() as session:
                session.run(
                    """
                    MERGE (u:User {user_id: $user_id})
                    MERGE (d:Device {device_id: $device_id})
                    MERGE (i:IP {ip: $ip})
                    MERGE (b:Bank {bank_id: $bank_id})
                    MERGE (u)-[:USES]->(d)
                    MERGE (d)-[:CONNECTED_TO]->(i)
                    MERGE (u)-[:BELONGS_TO]->(b)
                    """,
                    user_id=user_id,
                    device_id=device_id,
                    ip=ip,
                    bank_id=bank_id,
                )
        except Exception as exc:
            logger.warning("Neo4j log_activity failed: %s. Falling back to MongoDB mock graph.", exc)
            self._log_activity_fallback(user_id, device_id, ip, bank_id)

    def detect_device_reuse(self, device_id):
        if self.driver is None:
            return self._detect_device_reuse_fallback(device_id)
        try:
            with self.driver.session() as session:
                result = session.run(
                    """
                    MATCH (d:Device {device_id: $device_id})<-[:USES]-(u:User)
                    WITH d, COUNT(DISTINCT u) AS user_count
                    RETURN user_count
                    """,
                    device_id=device_id,
                )
                record = result.single()
                return record['user_count'] if record else 0
        except Exception as exc:
            logger.warning("Neo4j detect_device_reuse failed: %s. Falling back to MongoDB mock graph.", exc)
            return self._detect_device_reuse_fallback(device_id)

    def detect_ip_rotation(self, device_id):
        if self.driver is None:
            return self._detect_ip_rotation_fallback(device_id)
        try:
            with self.driver.session() as session:
                result = session.run(
                    """
                    MATCH (d:Device {device_id: $device_id})-[:CONNECTED_TO]->(i:IP)
                    WITH d, COUNT(DISTINCT i) AS ip_count
                    RETURN ip_count
                    """,
                    device_id=device_id,
                )
                record = result.single()
                return record['ip_count'] if record else 0
        except Exception as exc:
            logger.warning("Neo4j detect_ip_rotation failed: %s. Falling back to MongoDB mock graph.", exc)
            return self._detect_ip_rotation_fallback(device_id)

    def detect_cross_bank(self, device_id):
        if self.driver is None:
            return self._detect_cross_bank_fallback(device_id)
        try:
            with self.driver.session() as session:
                result = session.run(
                    """
                    MATCH (d:Device {device_id: $device_id})<-[:USES]-(u:User)-[:BELONGS_TO]->(b:Bank)
                    WITH d, COUNT(DISTINCT b) AS bank_count
                    RETURN bank_count
                    """,
                    device_id=device_id,
                )
                record = result.single()
                return record['bank_count'] if record else 0
        except Exception as exc:
            logger.warning("Neo4j detect_cross_bank failed: %s. Falling back to MongoDB mock graph.", exc)
            return self._detect_cross_bank_fallback(device_id)

    def get_graph_data(self, bank_id=None, user_id=None):
        if self.driver is None:
            return self._get_graph_data_fallback(bank_id, user_id)
        try:
            nodes = []
            edges = []
            with self.driver.session() as session:
                if bank_id and user_id:
                    results = session.run(
                        """
                        MATCH p=(b:Bank {bank_id: $bank_id})<-[:BELONGS_TO]-(u:User {user_id: $user_id})-[:USES]->(:Device)-[:CONNECTED_TO]->(:IP)
                        UNWIND relationships(p) AS rel
                        WITH rel, startNode(rel) AS n, endNode(rel) AS m
                        RETURN DISTINCT n, rel AS r, m
                        LIMIT 300
                        """,
                        bank_id=bank_id,
                        user_id=user_id,
                    )
                elif bank_id:
                    results = session.run(
                        """
                        MATCH p=(b:Bank {bank_id: $bank_id})<-[:BELONGS_TO]-(u:User)-[:USES]->(:Device)-[:CONNECTED_TO]->(:IP)
                        UNWIND relationships(p) AS rel
                        WITH rel, startNode(rel) AS n, endNode(rel) AS m
                        RETURN DISTINCT n, rel AS r, m
                        LIMIT 300
                        """,
                        bank_id=bank_id,
                    )
                else:
                    results = session.run(
                        """
                        MATCH p=(n)-[r]->(m)
                        RETURN n, r, m LIMIT 100
                        """
                    )

                node_set = set()
                for record in results:
                    n = record['n']
                    m = record['m']
                    r = record['r']

                    n_id = n.element_id
                    m_id = m.element_id

                    if n_id not in node_set:
                        label = list(n.labels)[0] if n.labels else 'Unknown'
                        nodes.append({'id': n_id, 'label': label, 'properties': dict(n.items())})
                        node_set.add(n_id)
                    if m_id not in node_set:
                        label = list(m.labels)[0] if m.labels else 'Unknown'
                        nodes.append({'id': m_id, 'label': label, 'properties': dict(m.items())})
                        node_set.add(m_id)

                    edges.append({
                        'source': n_id,
                        'target': m_id,
                        'type': r.type
                    })
            return {'nodes': nodes, 'edges': edges}
        except Exception as exc:
            logger.warning("Neo4j get_graph_data failed: %s. Falling back to MongoDB mock graph.", exc)
            return self._get_graph_data_fallback(bank_id, user_id)

    def get_graph_insights(self, bank_id=None):
        if self.driver is None:
            return self._get_graph_insights_fallback(bank_id)
        try:
            insights = []
            with self.driver.session() as session:
                if bank_id:
                    device_reuse = session.run(
                        """
                        MATCH (:Bank {bank_id: $bank_id})<-[:BELONGS_TO]-(u:User)-[:USES]->(d:Device)
                        WITH d.device_id AS device_id, COUNT(DISTINCT u) AS user_count
                        WHERE user_count > 1
                        RETURN device_id, user_count
                        ORDER BY user_count DESC
                        LIMIT 25
                        """,
                        bank_id=bank_id,
                    )
                    for record in device_reuse:
                        insights.append(
                            f"Device Reuse Warning: Device {record['device_id']} is used by {record['user_count']} users."
                        )

                    botnets = session.run(
                        """
                        MATCH (:Bank {bank_id: $bank_id})<-[:BELONGS_TO]-(u:User)-[:USES]->(:Device)-[:CONNECTED_TO]->(i:IP)
                        WITH i.ip AS ip, COUNT(DISTINCT u) AS user_count
                        WHERE user_count > 3
                        RETURN ip, user_count
                        ORDER BY user_count DESC
                        LIMIT 25
                        """,
                        bank_id=bank_id,
                    )
                else:
                    botnets = session.run(
                        """
                        MATCH (i:IP)<-[:CONNECTED_TO]-(d:Device)<-[:USES]-(u:User)
                        WITH i.ip AS ip, COUNT(DISTINCT u) AS user_count
                        WHERE user_count > 3
                        RETURN ip, user_count
                        """
                    )
                for record in botnets:
                    insights.append(
                        f"Botnet Warning: IP {record['ip']} is connected to {record['user_count']} users."
                    )

                if bank_id:
                    rotations = session.run(
                        """
                        MATCH (:Bank {bank_id: $bank_id})<-[:BELONGS_TO]-(u:User)-[:USES]->(:Device)-[:CONNECTED_TO]->(i:IP)
                        WITH u.user_id AS user_id, COUNT(DISTINCT i) AS ip_count
                        WHERE ip_count > 3
                        RETURN user_id, ip_count
                        ORDER BY ip_count DESC
                        LIMIT 25
                        """,
                        bank_id=bank_id,
                    )

                    cross_bank = session.run(
                        """
                        MATCH (:Bank {bank_id: $bank_id})<-[:BELONGS_TO]-(:User)-[:USES]->(d:Device)
                        WITH DISTINCT d
                        MATCH (d)<-[:USES]-(:User)-[:BELONGS_TO]->(b:Bank)
                        WITH d.device_id AS device_id, COUNT(DISTINCT b) AS bank_count
                        WHERE bank_count > 1
                        RETURN device_id, bank_count
                        ORDER BY bank_count DESC
                        LIMIT 25
                        """,
                        bank_id=bank_id,
                    )
                    for record in cross_bank:
                        insights.append(
                            f"Cross-Bank Warning: Device {record['device_id']} is seen in {record['bank_count']} banks."
                        )
                else:
                    rotations = session.run(
                        """
                        MATCH (u:User)-[:USES]->(d:Device)-[:CONNECTED_TO]->(i:IP)
                        WITH u.user_id AS user_id, COUNT(DISTINCT i) AS ip_count
                        WHERE ip_count > 3
                        RETURN user_id, ip_count
                        """
                    )
                for record in rotations:
                    insights.append(
                        f"IP Rotation Warning: User {record['user_id']} is connected through {record['ip_count']} IPs."
                    )
            return insights
        except Exception as exc:
            logger.warning("Neo4j get_graph_insights failed: %s. Falling back to MongoDB mock graph.", exc)
            return self._get_graph_insights_fallback(bank_id)

    # ==========================================
    # MongoDB Mock Graph Fallbacks
    # ==========================================

    def _log_activity_fallback(self, user_id, device_id, ip, bank_id):
        from database.mongo import get_db
        db = get_db()
        if db is None:
            return
        
        user_node_id = f"User:{user_id}"
        device_node_id = f"Device:{device_id}"
        ip_node_id = f"IP:{ip}"
        bank_node_id = f"Bank:{bank_id}"

        # Insert/update nodes
        db.graph_nodes.update_one({"id": user_node_id}, {"$set": {"id": user_node_id, "label": "User", "properties": {"user_id": user_id}}}, upsert=True)
        db.graph_nodes.update_one({"id": device_node_id}, {"$set": {"id": device_node_id, "label": "Device", "properties": {"device_id": device_id}}}, upsert=True)
        db.graph_nodes.update_one({"id": ip_node_id}, {"$set": {"id": ip_node_id, "label": "IP", "properties": {"ip": ip}}}, upsert=True)
        db.graph_nodes.update_one({"id": bank_node_id}, {"$set": {"id": bank_node_id, "label": "Bank", "properties": {"bank_id": bank_id}}}, upsert=True)

        # Insert/update edges
        db.graph_edges.update_one({"id": f"{user_node_id}->{device_node_id}"}, {"$set": {"id": f"{user_node_id}->{device_node_id}", "source": user_node_id, "target": device_node_id, "type": "USES"}}, upsert=True)
        db.graph_edges.update_one({"id": f"{device_node_id}->{ip_node_id}"}, {"$set": {"id": f"{device_node_id}->{ip_node_id}", "source": device_node_id, "target": ip_node_id, "type": "CONNECTED_TO"}}, upsert=True)
        db.graph_edges.update_one({"id": f"{user_node_id}->{bank_node_id}"}, {"$set": {"id": f"{user_node_id}->{bank_node_id}", "source": user_node_id, "target": bank_node_id, "type": "BELONGS_TO"}}, upsert=True)

    def _detect_device_reuse_fallback(self, device_id):
        from database.mongo import get_db
        db = get_db()
        if db is None:
            return 0
        device_node_id = f"Device:{device_id}"
        edges = list(db.graph_edges.find({"target": device_node_id, "type": "USES"}))
        users = set(edge['source'].replace("User:", "") for edge in edges)
        return len(users)

    def _detect_ip_rotation_fallback(self, device_id):
        from database.mongo import get_db
        db = get_db()
        if db is None:
            return 0
        device_node_id = f"Device:{device_id}"
        edges = list(db.graph_edges.find({"source": device_node_id, "type": "CONNECTED_TO"}))
        ips = set(edge['target'].replace("IP:", "") for edge in edges)
        return len(ips)

    def _detect_cross_bank_fallback(self, device_id):
        from database.mongo import get_db
        db = get_db()
        if db is None:
            return 0
        device_node_id = f"Device:{device_id}"
        user_edges = list(db.graph_edges.find({"target": device_node_id, "type": "USES"}))
        users = [edge['source'] for edge in user_edges]
        if not users:
            return 0
        bank_edges = list(db.graph_edges.find({"source": {"$in": users}, "type": "BELONGS_TO"}))
        banks = set(edge['target'].replace("Bank:", "") for edge in bank_edges)
        return len(banks)

    def _get_graph_data_fallback(self, bank_id=None, user_id=None):
        from database.mongo import get_db
        db = get_db()
        if db is None:
            return {'nodes': [], 'edges': []}

        nodes = []
        edges = []
        node_set = set()

        if bank_id and user_id:
            bank_node_id = f"Bank:{bank_id}"
            user_node_id = f"User:{user_id}"

            belongs = db.graph_edges.find_one({"source": user_node_id, "target": bank_node_id, "type": "BELONGS_TO"})
            if belongs:
                node_set.add(bank_node_id)
                node_set.add(user_node_id)
                edges.append({'source': user_node_id, 'target': bank_node_id, 'type': 'BELONGS_TO'})

                dev_edges = list(db.graph_edges.find({"source": user_node_id, "type": "USES"}))
                for edge in dev_edges:
                    dev_id = edge['target']
                    node_set.add(dev_id)
                    edges.append({'source': user_node_id, 'target': dev_id, 'type': 'USES'})

                    ip_edges = list(db.graph_edges.find({"source": dev_id, "type": "CONNECTED_TO"}))
                    for ip_edge in ip_edges:
                        ip_id = ip_edge['target']
                        node_set.add(ip_id)
                        edges.append({'source': dev_id, 'target': ip_id, 'type': 'CONNECTED_TO'})

        elif bank_id:
            bank_node_id = f"Bank:{bank_id}"
            user_edges = list(db.graph_edges.find({"target": bank_node_id, "type": "BELONGS_TO"}))
            node_set.add(bank_node_id)
            for u_edge in user_edges:
                user_id = u_edge['source']
                node_set.add(user_id)
                edges.append({'source': user_id, 'target': bank_node_id, 'type': 'BELONGS_TO'})

                dev_edges = list(db.graph_edges.find({"source": user_id, "type": "USES"}))
                for edge in dev_edges:
                    dev_id = edge['target']
                    node_set.add(dev_id)
                    edges.append({'source': user_id, 'target': dev_id, 'type': 'USES'})

                    ip_edges = list(db.graph_edges.find({"source": dev_id, "type": "CONNECTED_TO"}))
                    for ip_edge in ip_edges:
                        ip_id = ip_edge['target']
                        node_set.add(ip_id)
                        edges.append({'source': dev_id, 'target': ip_id, 'type': 'CONNECTED_TO'})
        else:
            all_edges = list(db.graph_edges.find().limit(100))
            for edge in all_edges:
                node_set.add(edge['source'])
                node_set.add(edge['target'])
                edges.append({'source': edge['source'], 'target': edge['target'], 'type': edge['type']})

        if node_set:
            db_nodes = list(db.graph_nodes.find({"id": {"$in": list(node_set)}}))
            for node in db_nodes:
                nodes.append({
                    'id': node['id'],
                    'label': node['label'],
                    'properties': node.get('properties', {})
                })

        return {'nodes': nodes, 'edges': edges}

    def _get_graph_insights_fallback(self, bank_id=None):
        from database.mongo import get_db
        db = get_db()
        insights = []
        if db is None:
            return insights

        dev_ips = list(db.graph_edges.find({"type": "CONNECTED_TO"}))
        usr_devs = list(db.graph_edges.find({"type": "USES"}))
        usr_banks = list(db.graph_edges.find({"type": "BELONGS_TO"}))

        bank_users = set()
        if bank_id:
            bank_node_id = f"Bank:{bank_id}"
            bank_users = set(e['source'] for e in usr_banks if e['target'] == bank_node_id)

        # 1. Device Reuse
        dev_users = {}
        for edge in usr_devs:
            if not bank_id or edge['source'] in bank_users:
                dev_users.setdefault(edge['target'], set()).add(edge['source'])
        for dev_node_id, users in dev_users.items():
            if len(users) > 1:
                dev_id = dev_node_id.replace("Device:", "")
                insights.append(f"Device Reuse Warning: Device {dev_id} is used by {len(users)} users.")

        # 2. Botnets
        dev_to_ips = {}
        for edge in dev_ips:
            dev_to_ips.setdefault(edge['source'], set()).add(edge['target'])

        ip_users = {}
        for edge in usr_devs:
            user = edge['source']
            device = edge['target']
            if device in dev_to_ips:
                for ip in dev_to_ips[device]:
                    if not bank_id or user in bank_users:
                        ip_users.setdefault(ip, set()).add(user)
        for ip, users in ip_users.items():
            if len(users) > 3:
                ip_addr = ip.replace("IP:", "")
                insights.append(f"Botnet Warning: IP {ip_addr} is connected to {len(users)} users.")

        # 3. IP Rotations
        user_ips = {}
        for edge in usr_devs:
            user = edge['source']
            device = edge['target']
            if device in dev_to_ips:
                for ip in dev_to_ips[device]:
                    if not bank_id or user in bank_users:
                        user_ips.setdefault(user, set()).add(ip)
        for user, ips in user_ips.items():
            if len(ips) > 3:
                u_id = user.replace("User:", "")
                insights.append(f"IP Rotation Warning: User {u_id} is connected through {len(ips)} IPs.")

        # 4. Cross-Bank
        usr_to_banks = {}
        for edge in usr_banks:
            usr_to_banks.setdefault(edge['source'], set()).add(edge['target'])

        dev_banks = {}
        for edge in usr_devs:
            user = edge['source']
            device = edge['target']
            if user in usr_to_banks:
                for bank in usr_to_banks[user]:
                    dev_banks.setdefault(device, set()).add(bank)
        for device, banks in dev_banks.items():
            if len(banks) > 1:
                if not bank_id or any(bank.replace("Bank:", "") == bank_id for bank in banks):
                    dev_id = device.replace("Device:", "")
                    insights.append(f"Cross-Bank Warning: Device {dev_id} is seen in {len(banks)} banks.")

        return insights


graph_db_instance = None


def init_neo4j(app):
    global graph_db_instance
    uri = app.config.get('NEO4J_URI', 'bolt://localhost:7687')
    user = app.config.get('NEO4J_USER', 'neo4j')
    password = app.config.get('NEO4J_PASSWORD', 'password')
    graph_db_instance = GraphDB(uri, user, password)


def get_graph():
    return graph_db_instance
