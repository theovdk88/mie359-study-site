const data = await fetch("./data/site.json").then((response) => response.json());

const state = {
  site: data,
  progress: loadProgress(),
};

const appEl = document.querySelector("#app");
const navEl = document.querySelector("#sidebar-nav");
const breadcrumbEl = document.querySelector("#breadcrumbs");
const progressEl = document.querySelector("#progress-pill");

renderNav();
window.addEventListener("hashchange", renderRoute);
renderRoute();

function renderRoute() {
  const hash = window.location.hash || "#/";
  const parts = hash.replace(/^#\/?/, "").split("/").filter(Boolean);
  const route = parts[0] || "home";
  const id = parts[1];

  if (route === "home") {
    setFrame("Home", "Study hub");
    appEl.innerHTML = renderHome();
    return;
  }

  if (route === "chapter" && id) {
    const chapter = getChapter(id);
    if (!chapter) return renderMissing();
    markChapterViewed(id);
    setFrame(chapter.title, chapter.topic_type === "guest" ? "Guest lecture" : "Chapter notes");
    appEl.innerHTML = renderChapter(chapter);
    attachFlashcardDeck(`chapter-${chapter.id}`, chapter.flashcards);
    return;
  }

  if (route === "flashcards" && id) {
    const chapter = getChapter(id);
    if (!chapter) return renderMissing();
    setFrame(`${chapter.title}`, "Flashcards");
    appEl.innerHTML = renderFlashcards(chapter);
    attachFlashcardHandlers(chapter);
    return;
  }

  if (route === "quiz" && id) {
    const chapter = getChapter(id);
    if (!chapter) return renderMissing();
    setFrame(`${chapter.title}`, "Chapter quiz");
    appEl.innerHTML = renderQuiz(chapter.title, chapter.id, chapter.quiz, "chapter");
    attachQuizHandlers(chapter.id, chapter.title, chapter.quiz, "chapter");
    return;
  }

  if (route === "cumulative" && id) {
    const cumulative = state.site.cumulative_quizzes.find((entry) => entry.chapter_id === id);
    if (!cumulative) return renderMissing();
    setFrame(cumulative.title, "Cumulative quiz");
    appEl.innerHTML = renderQuiz(cumulative.title, id, cumulative.questions, "cumulative");
    attachQuizHandlers(id, cumulative.title, cumulative.questions, "cumulative");
    return;
  }

  if (route === "final") {
    setFrame("Final Exam Mode", "Mixed review");
    appEl.innerHTML = renderQuiz("Final Exam Mode", "final", state.site.final_exam.questions, "final");
    attachQuizHandlers("final", "Final Exam Mode", state.site.final_exam.questions, "final");
    return;
  }

  if (route === "definitions") {
    setFrame("Definitions Index", "Course-wide glossary");
    appEl.innerHTML = renderDefinitions();
    return;
  }

  if (route === "weak-topics") {
    setFrame("Weak Topic Review", "Retry the ideas you missed");
    appEl.innerHTML = renderWeakTopics();
    return;
  }

  renderMissing();
}

function renderNav() {
  const chapterLinks = state.site.chapters
    .map((chapter) => {
      const tag = chapter.topic_type === "guest" ? '<span class="nav-tag">Guest</span>' : "";
      return `
        <a class="nav-link" href="#/chapter/${chapter.id}">
          <span>${chapter.nav_title}</span>
          ${tag}
        </a>
      `;
    })
    .join("");

  navEl.innerHTML = `
    <div class="nav-group">
      <p class="nav-label">Study</p>
      <a class="nav-link" href="#/">Home</a>
      ${chapterLinks}
    </div>
    <div class="nav-group">
      <p class="nav-label">Tools</p>
      <a class="nav-link" href="#/definitions">Definitions Index</a>
      <a class="nav-link" href="#/final">Final Exam Mode</a>
      <a class="nav-link" href="#/weak-topics">Weak Topic Review</a>
    </div>
  `;
}

function renderHome() {
  const chapterCards = state.site.chapters
    .map(
      (chapter) => `
        <article class="home-card note-card">
          <p class="mini-label">${chapter.topic_type === "guest" ? "Guest Lecture" : "Chapter"}</p>
          <h3>${escapeHtml(chapter.nav_title)}</h3>
          <p>${chapter.definition_count} definitions, ${chapter.flashcard_count} flashcards, ${chapter.quiz_count} quiz questions</p>
          <div class="card-actions">
            <a class="button-link" href="#/chapter/${chapter.id}">Study Notes</a>
            <a class="button-link subtle" href="#/flashcards/${chapter.id}">Flashcards</a>
            <a class="button-link subtle" href="#/quiz/${chapter.id}">Quiz</a>
          </div>
        </article>
      `,
    )
    .join("");

  return `
    <section class="hero note-card">
      <p class="eyebrow">Primary source: markdown chapters</p>
      <h2>Study from the cleaned chapter notes, then drill with flashcards and quizzes.</h2>
      <p>The visible study content on this site is generated from the markdown bundle in <code>mie359_codex_bundle/chapters</code> and ordered by <code>manifest.json</code>.</p>
      <div class="hero-actions">
        <a class="button-link" href="#/final">Start Final Exam Mode</a>
        <a class="button-link subtle" href="#/definitions">Browse Definitions</a>
      </div>
    </section>

    <section class="stats-grid">
      <article class="stat-card note-card">
        <p class="mini-label">Progress</p>
        <h3>${Object.keys(state.progress.viewedChapters).length}/${state.site.chapters.length}</h3>
        <p>chapters opened</p>
      </article>
      <article class="stat-card note-card">
        <p class="mini-label">Quizzes</p>
        <h3>${Object.keys(state.progress.quizScores).length}</h3>
        <p>quiz sessions recorded</p>
      </article>
      <article class="stat-card note-card">
        <p class="mini-label">Weak Topics</p>
        <h3>${state.progress.weakTopics.length}</h3>
        <p>questions saved for review</p>
      </article>
    </section>

    <section class="section-shell">
      <div class="section-heading">
        <p class="eyebrow">Ordered chapters</p>
        <h2>Course study guide</h2>
      </div>
      <div class="home-grid">${chapterCards}</div>
    </section>
  `;
}

function renderChapter(chapter) {
  const neighbors = getChapterNeighbors(chapter.id);
  const practiceHtml = chapter.practice_questions.length
    ? `
      <section class="section-shell">
        <div class="section-heading">
          <p class="eyebrow">Section 2</p>
          <h2>Chapter Practice Questions</h2>
        </div>
        <div class="note-card practice-shell">
          <ol class="practice-list">
          ${chapter.practice_questions
            .map(
              (question, index) => `
                <li class="practice-item">
                  <div class="practice-copy">
                    ${question.category ? `<p class="mini-label">${escapeHtml(question.category)}</p>` : ""}
                    <p>${escapeHtml(question.prompt)}</p>
                  </div>
                </li>
              `,
            )
            .join("")}
          </ol>
        </div>
      </section>
    `
    : "";

  return `
    <article class="chapter-page">
      <section class="chapter-hero note-card">
        <p class="eyebrow">${chapter.topic_type === "guest" ? "Guest Lecture" : "Chapter Study Guide"}</p>
        <h2>${escapeHtml(chapter.title)}</h2>
        <div class="chapter-hero-actions">
          ${neighbors.previous ? `<a class="button-link subtle" href="#/chapter/${neighbors.previous.id}">Previous Chapter</a>` : ""}
          ${neighbors.next ? `<a class="button-link subtle" href="#/chapter/${neighbors.next.id}">Next Chapter</a>` : ""}
          <a class="button-link" href="#/quiz/${chapter.id}">Chapter Quiz</a>
        </div>
      </section>

      ${chapter.overview_html || ""}

      <section class="section-shell">
        <div class="section-heading">
          <p class="eyebrow">Section 1</p>
          <h2>Concepts and Definitions</h2>
        </div>
        <div class="content-flow">${chapter.content_html}</div>
      </section>

      ${practiceHtml}

      <section class="section-shell">
        <div class="section-heading">
          <p class="eyebrow">Section 3</p>
          <h2>Flashcards</h2>
        </div>
        ${renderFlashcardDeck(chapter, `chapter-${chapter.id}`, true)}
        <div class="quick-links note-card">
          <a class="button-link" href="#/flashcards/${chapter.id}">Flashcard Mode</a>
          <a class="button-link subtle" href="#/quiz/${chapter.id}">Chapter Quiz</a>
          <a class="button-link subtle" href="#/cumulative/${chapter.id}">Cumulative Quiz</a>
          <a class="button-link subtle" href="#/final">Final Exam Mode</a>
        </div>
      </section>
    </article>
  `;
}

function renderFlashcards(chapter) {
  return `
    <section class="section-shell">
      <div class="section-heading">
        <p class="eyebrow">Flashcards</p>
        <h2>${escapeHtml(chapter.title)}</h2>
      </div>
      ${renderFlashcardDeck(chapter, `deck-${chapter.id}`, false)}
    </section>
  `;
}

function attachFlashcardHandlers(chapter) {
  attachFlashcardDeck(`deck-${chapter.id}`, chapter.flashcards);
}

function renderFlashcardDeck(chapter, prefix, compact) {
  const total = chapter.flashcards.length;
  const firstKind = total ? formatFlashcardKind(chapter.flashcards[0].kind) : "";
  return `
    <div class="flashcard-controls note-card">
      <button class="button-link subtle" id="${prefix}-prev-card" type="button">Previous</button>
      <div class="flashcard-status">
        <p id="${prefix}-flashcard-count">${total ? "1" : "0"} / ${total}</p>
        <span class="flashcard-kind" id="${prefix}-flashcard-kind">${escapeHtml(firstKind)}</span>
      </div>
      <button class="button-link subtle" id="${prefix}-next-card" type="button">Next</button>
    </div>
    <button class="flashcard note-card ${compact ? "flashcard-compact" : ""}" id="${prefix}-flashcard" type="button">
      <span class="flashcard-label">Prompt</span>
      <h3 id="${prefix}-flashcard-front">${total ? escapeHtml(chapter.flashcards[0].front) : "No flashcards available."}</h3>
      <p id="${prefix}-flashcard-back" class="flashcard-back" hidden>${total ? escapeHtml(chapter.flashcards[0].back) : ""}</p>
      <span class="flashcard-hint">${total ? "Click to reveal the answer" : ""}</span>
    </button>
  `;
}

function attachFlashcardDeck(prefix, cards) {
  const cardEl = document.querySelector(`#${prefix}-flashcard`);
  if (!cardEl || !cards.length) return;

  const frontEl = document.querySelector(`#${prefix}-flashcard-front`);
  const backEl = document.querySelector(`#${prefix}-flashcard-back`);
  const countEl = document.querySelector(`#${prefix}-flashcard-count`);
  const kindEl = document.querySelector(`#${prefix}-flashcard-kind`);
  const labelEl = cardEl.querySelector(".flashcard-label");
  const hintEl = cardEl.querySelector(".flashcard-hint");
  let index = 0;
  let flipped = false;

  const sync = () => {
    const card = cards[index];
    frontEl.textContent = card.front;
    backEl.textContent = card.back;
    backEl.hidden = !flipped;
    cardEl.classList.toggle("is-flipped", flipped);
    countEl.textContent = `${index + 1} / ${cards.length}`;
    if (kindEl) kindEl.textContent = formatFlashcardKind(card.kind);
    if (labelEl) labelEl.textContent = flipped ? "Answer" : "Prompt";
    if (hintEl) hintEl.textContent = flipped ? "Click to return to the prompt" : "Click to reveal the answer";
  };

  cardEl.addEventListener("click", () => {
    flipped = !flipped;
    sync();
  });

  document.querySelector(`#${prefix}-prev-card`)?.addEventListener("click", () => {
    index = (index - 1 + cards.length) % cards.length;
    flipped = false;
    sync();
  });

  document.querySelector(`#${prefix}-next-card`)?.addEventListener("click", () => {
    index = (index + 1) % cards.length;
    flipped = false;
    sync();
  });
}

function formatFlashcardKind(kind) {
  const labels = {
    definition: "Definition",
    recognition: "Concept recognition",
    framework: "Framework",
    comparison: "Comparison",
    example: "Scenario",
  };
  return labels[kind] || "Flashcard";
}

function renderQuiz(title, id, questions, mode) {
  if (!questions.length) {
    return `<section class="note-card"><h2>${escapeHtml(title)}</h2><p>No quiz questions were generated for this topic.</p></section>`;
  }

  const items = questions
    .map(
      (question, index) => renderQuizQuestion(question, index),
    )
    .join("");

  return `
    <section class="section-shell">
      <div class="section-heading">
        <p class="eyebrow">${escapeHtml(mode)}</p>
        <h2>${escapeHtml(title)}</h2>
      </div>
      <form id="quiz-form" class="quiz-form">
        ${items}
        <div class="quiz-actions">
          <button class="button-link" type="submit">Submit Quiz</button>
          <a class="button-link subtle" href="#/weak-topics">Weak Topic Review</a>
        </div>
      </form>
      <section id="quiz-results"></section>
    </section>
  `;
}

function renderQuizQuestion(question, index) {
  const meta = `
    <div class="quiz-meta-row">
      <p class="mini-label">Question ${index + 1}</p>
      <span class="quiz-kind">${escapeHtml(formatQuizKind(question.type, question.source_kind))}</span>
    </div>
  `;

  if (question.type === "self_check") {
    return `
      <article class="quiz-card note-card quiz-card-self-check" data-question-type="self_check" data-index="${index}">
        ${meta}
        <h3>${escapeHtml(question.prompt)}</h3>
        <div class="self-check-tools">
          <button class="button-link subtle self-check-reveal" type="button" data-index="${index}">Reveal Answer</button>
          <button class="button-link subtle self-check-mark" type="button" data-index="${index}" data-result="got_it">I Got It</button>
          <button class="button-link subtle self-check-mark" type="button" data-index="${index}" data-result="missed">I Missed It</button>
        </div>
        <div class="self-check-answer" id="self-check-answer-${index}" hidden>
          <p class="mini-label">Model Answer</p>
          <p>${escapeHtml(question.answer)}</p>
        </div>
        <p class="self-check-status" id="self-check-status-${index}">Use this as a self-check prompt, then reveal the answer and mark how you did.</p>
      </article>
    `;
  }

  return `
    <article class="quiz-card note-card" data-question-type="multiple_choice" data-index="${index}">
      ${meta}
      <h3>${escapeHtml(question.prompt)}</h3>
      <div class="quiz-options">
        ${question.options
          .map(
            (option) => `
              <label class="quiz-option">
                <input type="radio" name="q-${index}" value="${escapeAttribute(option)}">
                <span>${escapeHtml(option)}</span>
              </label>
            `,
          )
          .join("")}
      </div>
    </article>
  `;
}

function formatQuizKind(type, sourceKind) {
  if (type === "self_check") return "Self-check";
  if (sourceKind === "framework") return "Framework MC";
  if (sourceKind === "example") return "Scenario MC";
  if (sourceKind === "definition_match") return "Concept MC";
  if (sourceKind === "recognition") return "Concept MC";
  return "Quiz";
}

function displayQuizAnswer(question) {
  if (question.answer_label && question.answer_label !== question.answer) {
    return `${question.answer_label}: ${question.answer}`;
  }
  return question.answer;
}

function attachQuizHandlers(chapterId, title, questions, mode) {
  const form = document.querySelector("#quiz-form");
  const resultsEl = document.querySelector("#quiz-results");
  if (!form || !resultsEl) return;
  const selfCheckState = new Map();

  form.querySelectorAll(".self-check-reveal").forEach((button) => {
    button.addEventListener("click", () => {
      const index = Number(button.dataset.index);
      const current = selfCheckState.get(index) || {};
      selfCheckState.set(index, { ...current, revealed: true });
      syncSelfCheckCard(index, selfCheckState);
    });
  });

  form.querySelectorAll(".self-check-mark").forEach((button) => {
    button.addEventListener("click", () => {
      const index = Number(button.dataset.index);
      const result = button.dataset.result;
      const current = selfCheckState.get(index) || {};
      selfCheckState.set(index, { ...current, result, revealed: current.revealed ?? false });
      syncSelfCheckCard(index, selfCheckState);
    });
  });

  form.addEventListener("submit", (event) => {
    event.preventDefault();
    const payload = questions.map((question, index) => {
      if (question.type === "self_check") {
        const stateForQuestion = selfCheckState.get(index) || { revealed: false, result: "" };
        return {
          question,
          selected: stateForQuestion.result || "",
          correct: stateForQuestion.result !== "missed",
          reviewed: Boolean(stateForQuestion.revealed || stateForQuestion.result),
        };
      }
      const choice = form.querySelector(`input[name="q-${index}"]:checked`);
      return {
        question,
        selected: choice?.value || "",
        correct: choice?.value === question.answer,
        reviewed: Boolean(choice?.value),
      };
    });

    const multipleChoice = payload.filter((entry) => entry.question.type === "multiple_choice");
    const score = multipleChoice.filter((entry) => entry.correct).length;
    const wrong = multipleChoice.filter((entry) => !entry.correct);
    const selfCheck = payload.filter((entry) => entry.question.type === "self_check");
    const missedSelfChecks = selfCheck.filter((entry) => entry.selected === "missed");
    const reviewedSelfChecks = selfCheck.filter((entry) => entry.reviewed).length;

    state.progress.quizScores[`${mode}:${chapterId}:${Date.now()}`] = {
      chapterId,
      title,
      score,
      total: multipleChoice.length,
      selfCheckReviewed: reviewedSelfChecks,
      selfCheckTotal: selfCheck.length,
    };
    wrong.forEach((entry) => saveWeakTopic(chapterId, title, entry.question.prompt, displayQuizAnswer(entry.question), { type: "multiple_choice", source_kind: entry.question.source_kind }));
    missedSelfChecks.forEach((entry) => saveWeakTopic(chapterId, title, entry.question.prompt, displayQuizAnswer(entry.question), { type: "self_check", source_kind: entry.question.source_kind }));
    persistProgress();
    updateProgressPill();

    resultsEl.innerHTML = `
      <section class="note-card results-card">
        <p class="eyebrow">Results</p>
        <h3>${multipleChoice.length ? `${score} / ${multipleChoice.length}` : "Self-check set complete"}</h3>
        <p>
          ${
            wrong.length || missedSelfChecks.length
              ? "Missed items were added to Weak Topic Review."
              : "No misses recorded in this round."
          }
        </p>
        <p class="results-summary">
          ${multipleChoice.length ? `Multiple-choice scored: ${score}/${multipleChoice.length}. ` : ""}
          ${selfCheck.length ? `Self-check reviewed: ${reviewedSelfChecks}/${selfCheck.length}. Missed self-checks: ${missedSelfChecks.length}.` : ""}
        </p>
        ${
          wrong.length || missedSelfChecks.length
            ? `
              <div class="results-list">
                ${[...wrong, ...missedSelfChecks]
                  .map(
                    (entry) => `
                      <article class="result-item">
                        <p class="mini-label">${escapeHtml(formatQuizKind(entry.question.type, entry.question.source_kind))}</p>
                        <p><strong>Prompt:</strong> ${escapeHtml(entry.question.prompt)}</p>
                        <p><strong>Correct answer:</strong> ${escapeHtml(displayQuizAnswer(entry.question))}</p>
                      </article>
                    `,
                  )
                  .join("")}
              </div>
            `
            : ""
        }
      </section>
    `;
  });
}

function syncSelfCheckCard(index, selfCheckState) {
  const cardEl = document.querySelector(`.quiz-card-self-check[data-index="${index}"]`);
  const answerEl = document.querySelector(`#self-check-answer-${index}`);
  const statusEl = document.querySelector(`#self-check-status-${index}`);
  if (!cardEl || !answerEl || !statusEl) return;

  const current = selfCheckState.get(index) || { revealed: false, result: "" };
  answerEl.hidden = !current.revealed;
  cardEl.classList.toggle("is-reviewed", Boolean(current.revealed));
  cardEl.classList.toggle("is-missed", current.result === "missed");
  cardEl.classList.toggle("is-got-it", current.result === "got_it");

  cardEl.querySelectorAll(".self-check-mark").forEach((button) => {
    button.classList.toggle("is-selected", button.dataset.result === current.result);
  });

  if (current.result === "missed") {
    statusEl.textContent = "Marked as missed. This will be saved to Weak Topic Review when you submit.";
  } else if (current.result === "got_it") {
    statusEl.textContent = "Marked as correct.";
  } else if (current.revealed) {
    statusEl.textContent = "Answer revealed. Mark how you did.";
  } else {
    statusEl.textContent = "Use this as a self-check prompt, then reveal the answer and mark how you did.";
  }
}

function renderDefinitions() {
  const items = state.site.definitions
    .map(
      (entry) => `
        <article class="definition-card note-card">
          <p class="mini-label">${escapeHtml(entry.chapter_title)}</p>
          <h3>${escapeHtml(entry.term)}</h3>
          <p>${escapeHtml(entry.definition)}</p>
        </article>
      `,
    )
    .join("");

  return `
    <section class="section-shell">
      <div class="section-heading">
        <p class="eyebrow">Definitions Index</p>
        <h2>Course-wide glossary</h2>
      </div>
      <div class="definitions-grid">${items}</div>
    </section>
  `;
}

function renderWeakTopics() {
  if (!state.progress.weakTopics.length) {
    return `<section class="note-card"><h2>No weak topics saved yet.</h2><p>Quiz mistakes will show up here so you can revisit them later.</p></section>`;
  }

  const grouped = groupWeakTopics();
  return `
    <section class="section-shell">
      <div class="section-heading">
        <p class="eyebrow">Weak Topic Review</p>
        <h2>Questions to revisit</h2>
      </div>
      ${Object.entries(grouped)
        .map(
          ([chapter, items]) => `
            <section class="note-card weak-group">
              <h3>${escapeHtml(chapter)}</h3>
              <div class="results-list">
                ${items
                  .map(
                    (item) => `
                      <article class="result-item">
                        ${item.type ? `<p class="mini-label">${escapeHtml(formatQuizKind(item.type, item.source_kind))}</p>` : ""}
                        <p><strong>Prompt:</strong> ${escapeHtml(item.prompt)}</p>
                        <p><strong>Answer:</strong> ${escapeHtml(item.answer)}</p>
                      </article>
                    `,
                  )
                  .join("")}
              </div>
            </section>
          `,
        )
        .join("")}
    </section>
  `;
}

function groupWeakTopics() {
  return state.progress.weakTopics.reduce((accumulator, item) => {
    accumulator[item.title] ||= [];
    accumulator[item.title].push(item);
    return accumulator;
  }, {});
}

function setFrame(title, subtitle) {
  breadcrumbEl.innerHTML = `<p class="eyebrow">${escapeHtml(subtitle)}</p><h2>${escapeHtml(title)}</h2>`;
  updateProgressPill();
  highlightCurrentLink();
}

function updateProgressPill() {
  const viewed = Object.keys(state.progress.viewedChapters).length;
  progressEl.textContent = `${viewed}/${state.site.chapters.length} chapters opened`;
}

function markChapterViewed(id) {
  state.progress.viewedChapters[id] = true;
  persistProgress();
  updateProgressPill();
}

function saveWeakTopic(chapterId, title, prompt, answer, meta = {}) {
  const key = `${chapterId}:${prompt}`;
  const existing = state.progress.weakTopics.find((item) => item.key === key);
  if (existing) return;
  state.progress.weakTopics.push({ key, chapterId, title, prompt, answer, ...meta });
}

function getChapter(id) {
  return state.site.chapters.find((chapter) => chapter.id === id);
}

function getChapterNeighbors(id) {
  const index = state.site.chapters.findIndex((chapter) => chapter.id === id);
  return {
    previous: index > 0 ? state.site.chapters[index - 1] : null,
    next: index >= 0 && index < state.site.chapters.length - 1 ? state.site.chapters[index + 1] : null,
  };
}

function renderMissing() {
  setFrame("Not Found", "Route");
  appEl.innerHTML = `<section class="note-card"><h2>Page not found.</h2><p>Choose a chapter or study tool from the sidebar.</p></section>`;
}

function loadProgress() {
  try {
    return JSON.parse(localStorage.getItem("mie359-progress")) || {
      viewedChapters: {},
      quizScores: {},
      weakTopics: [],
    };
  } catch {
    return {
      viewedChapters: {},
      quizScores: {},
      weakTopics: [],
    };
  }
}

function persistProgress() {
  localStorage.setItem("mie359-progress", JSON.stringify(state.progress));
}

function highlightCurrentLink() {
  document.querySelectorAll(".nav-link").forEach((link) => {
    link.classList.toggle("is-active", link.getAttribute("href") === window.location.hash || (window.location.hash === "" && link.getAttribute("href") === "#/"));
  });
}

function escapeHtml(text) {
  return `${text}`
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function escapeAttribute(text) {
  return escapeHtml(text);
}
