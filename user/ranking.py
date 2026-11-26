"""
Ranking helpers for SearchLens.
 - compute_weight(path)  : your original NLP + LDA weight code, moved here (unchanged logic)
 - search_documents(q)   : searches filename AND file contents, returns ranked results
"""
import os
import re


# ---------------------------------------------------------------------------
# 1) Weight calculation (this is the code that used to live inside views.weight)
# ---------------------------------------------------------------------------
def _feature_names(vectorizer):
    # works on old and new scikit-learn versions
    if hasattr(vectorizer, "get_feature_names_out"):
        return list(vectorizer.get_feature_names_out())
    return list(vectorizer.get_feature_names())


def compute_weight(path):
    """Read the text file at `path` and return (weight, rank, label)."""
    # heavy libraries are imported here so the server starts fast
    import inflect
    import nltk
    from nltk.stem import WordNetLemmatizer
    from nltk.tokenize import word_tokenize
    from sklearn.feature_extraction.text import TfidfVectorizer
    from gensim import corpora, models

    with open(path, encoding="utf-8", errors="ignore") as f:
        texts = f.read()

    lower_text = texts.lower()
    rem_spe = re.sub(r"[^\w\s]", "", lower_text)

    p = inflect.engine()
    num_text = re.sub(r"\d+", lambda m: p.number_to_words(m.group()), rem_spe)
    num_text_processed = re.sub(r"[_,\-]", "", num_text)
    processed = re.sub(r"\n[\n]+", "\n", num_text_processed)
    stripped = processed.strip()

    stop = set(nltk.corpus.stopwords.words("english"))
    lemmatizer = WordNetLemmatizer()
    articles = [
        " ".join(lemmatizer.lemmatize(w) for w in word_tokenize(s) if w not in stop)
        for s in stripped.split("\n")
    ]

    tf_counter = TfidfVectorizer(max_features=1000, min_df=2, max_df=1.0)
    tf_counter.fit_transform(articles)
    vocab = set(_feature_names(tf_counter))

    processed_articles = [[x for x in a.split() if x in vocab] for a in articles]
    dictionary = corpora.Dictionary(processed_articles)
    corpus = [dictionary.doc2bow(t) for t in processed_articles]
    # random_state makes the result the same every time for the same file
    lda = models.ldamodel.LdaModel(corpus, num_topics=4, id2word=dictionary,
                                   passes=20, random_state=0)

    s = sum(prob for doc in lda.get_document_topics(corpus) for _, prob in doc)

    if s > 1000:
        rank = "1"
    elif s >= 200:
        rank = "2"
    elif s >= 100:
        rank = "3"
    elif s >= 50:
        rank = "4"
    else:
        rank = "5"
    label = 1 if s > 100 else 0
    return float(s), rank, label


def index_document(upload):
    """Create (or update) the search-table row for one uploaded file."""
    from user.models import weightmodel

    s, rank, label = compute_weight(upload.file.path)
    obj, _ = weightmodel.objects.update_or_create(
        file=upload.file.name,
        defaults={"filename": upload.filename, "weight": s,
                  "rank": rank, "label": label},
    )
    return obj


# ---------------------------------------------------------------------------
# 2) Search
# ---------------------------------------------------------------------------
def clean_query(q):
    """'  /Corona ' -> 'corona'  (removes spaces and a leading slash)."""
    return (q or "").strip().lstrip("/").strip()


def score_document(name, text, terms):
    """Pure function (easy to test). Returns (score, snippet) or None if no match."""
    name_l, text_l = name.lower(), text.lower()
    name_hits = sum(1 for t in terms if t in name_l)
    counts = [text_l.count(t) for t in terms]
    if not name_hits and not any(counts):
        return None
    score = sum(counts) + 10 * name_hits       # a name match counts extra

    snippet = ""
    first = [text_l.find(t) for t in terms if t in text_l]
    if first:
        i = min(first)
        start, end = max(0, i - 70), min(len(text), i + 150)
        snippet = re.sub(r"\s+", " ", text[start:end]).strip()
        if start > 0:
            snippet = "..." + snippet
        if end < len(text):
            snippet += "..."
    return score, snippet


def search_documents(query):
    from user.models import weightmodel

    terms = re.findall(r"\w+", clean_query(query).lower())
    if not terms:
        return []

    results = []
    for d in weightmodel.objects.all():
        try:
            with open(d.file.path, encoding="utf-8", errors="ignore") as f:
                text = f.read()
        except Exception:
            text = ""
        name = "%s %s" % (d.filename, os.path.basename(d.file.name))
        hit = score_document(name, text, terms)
        if not hit:
            continue
        try:
            w = float(d.weight)
        except (TypeError, ValueError):
            w = 0.0
        results.append({
            "filename": d.filename, "file": d.file.name, "weight": w,
            "rank": d.rank, "label": d.label,
            "score": hit[0], "snippet": hit[1],
        })
    # best match first: query score, then the ML weight as tie-breaker (numeric, not text!)
    results.sort(key=lambda r: (r["score"], r["weight"]), reverse=True)
    return results
