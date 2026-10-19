"""
Domain guard: ensures the chatbot ONLY answers Computer Science questions.
Uses a large keyword vocabulary + heuristics. 100% offline.
"""
import re
from difflib import SequenceMatcher


# ── Master vocabulary of CS terms grouped by subfield ──────────────
CS_VOCABULARY = {
    "ai_ml": {
        "ai", "artificial", "intelligence", "machine", "learning", "ml",
        "supervised", "unsupervised", "reinforcement", "regression",
        "classification", "clustering", "neural", "network", "neuron",
        "backpropagation", "gradient", "descent", "loss", "function",
        "overfitting", "underfitting", "bias", "variance", "feature",
        "training", "testing", "validation", "dataset", "label",
        "svm", "support", "vector", "machine", "random", "forest",
        "decision", "tree", "naive", "bayes", "knn", "k-means",
        "xgboost", "ensemble", "bagging", "boosting", "regularization",
        "cross", "validation", "confusion", "matrix", "precision",
        "recall", "f1", "roc", "auc", "hyperparameter", "tuning",
    },
    "dl": {
        "deep", "learning", "dl", "cnn", "convolutional", "rnn",
        "recurrent", "lstm", "gru", "transformer", "attention",
        "bert", "gpt", "llm", "gan", "autoencoder", "embedding",
        "tensorflow", "pytorch", "keras", "relu", "sigmoid", "softmax",
        "dropout", "batch", "normalization", "epoch", "layer",
        "pooling", "resnet", "vgg", "yolo", "diffusion", "generative",
    },
    "cybersecurity": {
        "cyber", "security", "hacking", "hacker", "penetration",
        "pen", "vulnerability", "exploit", "malware", "virus", "worm",
        "trojan", "ransomware", "phishing", "sql", "injection", "xss",
        "csrf", "ddos", "firewall", "encryption", "decryption",
        "cryptography", "hash", "sha", "aes", "rsa", "symmetric",
        "asymmetric", "public", "private", "key", "certificate",
        "ssl", "tls", "https", "authentication", "authorization",
        "oauth", "jwt", "salt", "brute", "force", "mitm", "zero",
        "day", "threat", "attack", "defense", "soc", "ids", "ips",
        "vpn", "proxy", "tor", "darknet", "steganography", "forensics",
    },
    "networking": {
        "network", "networking", "tcp", "ip", "udp", "http", "https",
        "dns", "dhcp", "arp", "icmp", "osi", "layer", "router",
        "switch", "hub", "gateway", "subnet", "subnetting", "cidr",
        "nat", "vlan", "lan", "wan", "man", "ethernet", "wifi",
        "wireless", "packet", "frame", "bandwidth", "latency",
        "throughput", "socket", "port", "protocol", "bgp", "ospf",
        "rip", "routing", "ipv4", "ipv6", "ssh", "ftp", "smtp",
        "imap", "pop3", "cdn", "load", "balancer", "proxy",
    },
    "programming": {
        "programming", "code", "coding", "language", "python", "java",
        "javascript", "c", "c++", "c#", "golang", "go", "rust",
        "ruby", "php", "swift", "kotlin", "typescript", "scala",
        "perl", "r", "matlab", "haskell", "lisp", "compiler",
        "interpreter", "syntax", "semantics", "variable", "loop",
        "function", "class", "object", "inheritance", "polymorphism",
        "encapsulation", "abstraction", "recursion", "iteration",
        "array", "list", "dictionary", "set", "tuple", "pointer",
        "reference", "memory", "stack", "heap", "garbage", "collection",
    },
    "dsa": {
        "data", "structure", "algorithm", "algorithms", "dsa",
        "array", "linked", "list", "stack", "queue", "tree", "graph",
        "heap", "hash", "table", "trie", "sorting", "searching",
        "binary", "search", "bubble", "merge", "quick", "heap",
        "insertion", "selection", "radix", "counting", "bfs", "dfs",
        "dijkstra", "bellman", "ford", "floyd", "warshall", "kruskal",
        "prim", "topological", "greedy", "dynamic", "programming",
        "backtracking", "divide", "conquer", "complexity", "big",
        "o", "theta", "omega", "np", "complete", "p", "vs", "recursion",
    },
    "software_engineering": {
        "software", "engineering", "sdlc", "agile", "scrum", "kanban",
        "waterfall", "devops", "ci", "cd", "continuous", "integration",
        "delivery", "deployment", "testing", "unit", "integration",
        "system", "acceptance", "tdd", "bdd", "refactoring", "design",
        "pattern", "solid", "mvc", "mvvm", "singleton", "factory",
        "observer", "decorator", "adapter", "strategy", "repository",
        "microservices", "monolith", "api", "rest", "graphql",
        "grpc", "soap", "versioning", "git", "github", "gitlab",
        "branch", "merge", "rebase", "pull", "request", "commit",
    },
    "web": {
        "web", "html", "css", "javascript", "frontend", "backend",
        "fullstack", "react", "angular", "vue", "svelte", "nextjs",
        "nuxt", "node", "express", "django", "flask", "fastapi",
        "spring", "laravel", "rails", "asp", "php", "jquery",
        "bootstrap", "tailwind", "sass", "less", "webpack", "vite",
        "dom", "ajax", "fetch", "axios", "cors", "cookie", "session",
        "localstorage", "responsive", "pwa", "spa", "ssr", "csr",
        "seo", "accessibility", "wcag", "webhook", "websocket",
    },
    "databases": {
        "database", "db", "sql", "nosql", "mysql", "postgresql",
        "postgres", "sqlite", "oracle", "mongodb", "redis", "cassandra",
        "neo4j", "elasticsearch", "table", "row", "column", "primary",
        "foreign", "key", "index", "join", "inner", "outer", "left",
        "right", "union", "group", "by", "having", "where", "select",
        "insert", "update", "delete", "transaction", "acid", "normalization",
        "1nf", "2nf", "3nf", "bcnf", "er", "diagram", "schema",
        "sharding", "replication", "partition", "cap", "theorem",
    },
    "os": {
        "operating", "system", "os", "kernel", "process", "thread",
        "concurrency", "parallelism", "deadlock", "semaphore", "mutex",
        "scheduling", "fcfs", "sjf", "round", "robin", "priority",
        "paging", "segmentation", "virtual", "memory", "cache",
        "tlb", "page", "fault", "thrashing", "swap", "file",
        "system", "inode", "unix", "linux", "windows", "macos",
        "shell", "bash", "command", "system", "call", "interrupt",
    },
    "theory": {
        "theory", "computation", "automata", "finite", "state",
        "machine", "turing", "regular", "expression", "grammar",
        "context", "free", "parser", "lexer", "compiler", "design",
        "tokenizer", "ast", "syntax", "tree", "pumping", "lemma",
        "decidable", "undecidable", "halting", "problem", "complexity",
        "np", "hard", "reduction", "sat", "clique", "vertex",
        "cover", "traveling", "salesman", "information", "coding",
        "shannon", "huffman", "entropy", "boolean", "logic", "gate",
    },
    "emerging": {
        "cloud", "aws", "azure", "gcp", "docker", "kubernetes",
        "container", "serverless", "lambda", "microservice",
        "blockchain", "bitcoin", "ethereum", "smart", "contract",
        "nft", "crypto", "web3", "quantum", "qubit", "entanglement",
        "iot", "embedded", "arduino", "raspberry", "edge", "5g",
        "ar", "vr", "xr", "metaverse", "digital", "twin",
        "big", "data", "hadoop", "spark", "kafka", "etl", "warehouse",
        "lake", "bi", "analytics", "visualization",
    },
}

# Flatten for fast lookup
ALL_CS_TERMS = set()
for terms in CS_VOCABULARY.values():
    ALL_CS_TERMS.update(terms)

# Multi-word CS phrases (weighted stronger)
CS_PHRASES = [
    "artificial intelligence", "machine learning", "deep learning",
    "neural network", "natural language", "computer vision",
    "data science", "big data", "cloud computing", "operating system",
    "computer network", "database management", "software engineering",
    "web development", "cyber security", "information security",
    "data structure", "dynamic programming", "time complexity",
    "space complexity", "object oriented", "functional programming",
    "version control", "design pattern", "system design",
    "problem solving", "discrete mathematics", "graph theory",
    "linear algebra", "probability statistics", "computer architecture",
    "compiler design", "theory of computation", "distributed system",
]

# Strong non-CS signals (immediately reject)
NON_CS_SIGNALS = {
    "recipe", "cook", "cooking", "food", "restaurant", "weather",
    "horoscope", "astrology", "cricket", "football", "soccer",
    "movie", "celebrity", "actor", "actress", "song", "music",
    "lyrics", "joke", "dating", "girlfriend", "boyfriend",
    "love", "marriage", "religion", "politics", "election",
    "doctor", "medicine", "hospital", "disease", "symptom",
    "law", "legal", "court", "police", "news", "stock", "trading",
    "gambling", "casino", "porn", "sex", "gossip", "shopping",
    "amazon", "flipkart", "coupon", "discount", "flight", "hotel",
}


def _normalize(text):
    text = text.lower().strip()
    text = re.sub(r"[^\w\s\-\+\#\.]", ' ', text)
    text = re.sub(r'\s+', ' ', text)
    return text


def _tokens(text):
    return [t for t in _normalize(text).split() if len(t) >= 2]


def _fuzzy_match(token, vocab, threshold=0.82):
    """Typo-tolerant match."""
    if token in vocab:
        return True
    for v in vocab:
        if abs(len(v) - len(token)) > 3:
            continue
        if SequenceMatcher(None, token, v).ratio() >= threshold:
            return True
    return False


def classify_domain(query):
    """
    Returns (is_cs: bool, confidence: float, category_hint: str|None)

    - is_cs=True  → allow search
    - is_cs=False → return polite refusal
    """
    if not query or len(query.strip()) < 2:
        return False, 0.0, None

    norm = _normalize(query)
    tokens = _tokens(query)

    # 1. Reject obvious non-CS
    if any(t in NON_CS_SIGNALS for t in tokens):
        return False, 0.0, None

    # 2. Phrase match (very strong signal)
    phrase_hits = [p for p in CS_PHRASES if p in norm]
    if phrase_hits:
        # Find which subfield this phrase belongs to
        for subfield, vocab in CS_VOCABULARY.items():
            for term in vocab:
                if term in phrase_hits[0]:
                    return True, 0.95, subfield

    # 3. Token match against vocabulary (with fuzzy fallback)
    subfield_scores = {}
    total_hits = 0

    for token in tokens:
        for subfield, vocab in CS_VOCABULARY.items():
            if _fuzzy_match(token, vocab):
                subfield_scores[subfield] = subfield_scores.get(subfield, 0) + 1
                total_hits += 1
                break

    if total_hits == 0:
        return False, 0.0, None

    # Coverage = how much of the query is CS-related
    coverage = total_hits / max(len(tokens), 1)

    # Require at least 30% coverage OR at least 2 hits
    if coverage < 0.3 and total_hits < 2:
        return False, coverage, None

    # Best subfield
    best_subfield = max(subfield_scores, key=subfield_scores.get)
    confidence = min(coverage + 0.15 * total_hits, 1.0)

    return True, round(confidence, 2), best_subfield


REFUSAL_MESSAGE = (
    "🤖 I'm a **Computer Science faculty assistant** — I only answer questions "
    "related to CS topics like:\n\n"
    "• 🤖 AI / Machine Learning / Deep Learning\n"
    "• 🔐 Cybersecurity\n"
    "• 🌐 Computer Networking\n"
    "• 💻 Programming Languages\n"
    "• 📊 Data Structures & Algorithms\n"
    "• 🏗️ Software Engineering\n"
    "• 🌍 Web Development\n"
    "• 🗄️ Databases\n"
    "• ⚙️ Operating Systems\n"
    "• 🧮 Theory of Computation\n"
    "• ☁️ Cloud & Emerging Tech\n\n"
    "Please rephrase your question with a CS topic, or pick one of the "
    "suggestions below."
)