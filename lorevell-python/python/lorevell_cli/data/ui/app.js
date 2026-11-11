"use strict";
const $ = (id) => document.getElementById(id);
const token = document.querySelector('meta[name="lorevell-token"]').content;
const state = {
  catalog: null,
  mode: "keyword",
  query: "",
  type: "",
  selected: "",
  searchSeq: 0,
  noteSeq: 0,
  saving: false,
};
let searchAbort, noteAbort, toastTimer;
function el(tag, cls, text) {
  const node = document.createElement(tag);
  if (cls) node.className = cls;
  if (text !== undefined) node.textContent = text;
  return node;
}
function button(text, action, cls = "") {
  const node = el("button", cls, text);
  node.type = "button";
  node.addEventListener("click", action);
  return node;
}
function error(message) {
  $("error").textContent = message || "";
  $("error").hidden = !message;
}
function toast(message) {
  $("toast").textContent = message;
  $("toast").hidden = false;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => ($("toast").hidden = true), 2400);
}
async function api(path, options = {}) {
  const response = await fetch(path, {
    ...options,
    headers: {
      "X-Lorevell-Token": token,
      ...(options.body ? { "Content-Type": "application/json" } : {}),
      ...options.headers,
    },
  });
  const data = await response.json();
  if (!response.ok)
    throw new Error(data.error || "The vault could not be read.");
  return data;
}
function urlFor(note = state.selected) {
  const url = new URL(location.href);
  url.search = "";
  if (state.query) url.searchParams.set("q", state.query);
  if (state.type) url.searchParams.set("type", state.type);
  if (state.mode === "hybrid") url.searchParams.set("mode", "hybrid");
  if (note) url.searchParams.set("note", note);
  return url;
}
function remember(replace = false) {
  history[replace ? "replaceState" : "pushState"]({}, "", urlFor());
}
function titleOf(note) {
  return (
    note.content
      ?.split("\n")
      .find((line) => line.startsWith("# "))
      ?.slice(2)
      .trim() ||
    note.title ||
    note.path
  );
}
function setMode(mode) {
  state.mode = mode;
  document
    .querySelectorAll("[data-mode]")
    .forEach((b) =>
      b.setAttribute("aria-pressed", String(b.dataset.mode === mode)),
    );
  $("modeHelp").textContent =
    mode === "hybrid"
      ? "Meaning + keywords. Local model; first use may download it."
      : "Fast, offline search. Words and their variations.";
}
async function catalog() {
  const data = await api("/api/catalog");
  state.catalog = data;
  $("vaultPath").textContent = data.name;
  $("vaultPath").title = data.vault;
  $("indexStatus").textContent = `${data.total} notes · refreshed just now`;
  $("typeFilter").replaceChildren(new Option("All types", ""));
  for (const type of data.types)
    if (type)
      $("typeFilter").append(
        new Option(type.charAt(0).toUpperCase() + type.slice(1), type),
      );
  $("typeFilter").value = state.type;
  if ($("typeFilter").value !== state.type) state.type = "";
  return data;
}
function resultRow(note, context = false) {
  const node = button(
    "",
    () => readNote(note.id, true),
    `result${note.id === state.selected ? " selected" : ""}`,
  );
  node.dataset.id = note.id;
  node.setAttribute("aria-pressed", String(note.id === state.selected));
  node.append(
    el("span", "kind", context ? "Connected note" : note.type || "Note"),
    el("strong", "", note.title),
    el("p", "", note.excerpt),
    el("div", "path", note.path),
  );
  return node;
}
function renderResults(notes, context = []) {
  $("results").replaceChildren();
  $("resultsLabel").textContent = state.query ? "Search results" : "Your notes";
  $("resultCount").textContent = String(notes.length);
  if (notes.length)
    for (const note of notes) $("results").append(resultRow(note));
  else {
    const box = el("div", "empty");
    box.append(
      el(
        "h3",
        "",
        state.catalog.total
          ? "Nothing found, yet."
          : "Start with one useful lesson.",
      ),
      el(
        "p",
        "",
        state.catalog.total
          ? "Try fewer words, a different note type, or hybrid search."
          : "Save a procedure, a decision, or a pitfall. Find it here when you need it.",
      ),
    );
    if (state.catalog.total)
      box.append(
        button(
          "Show all notes",
          () => {
            state.type = "";
            $("typeFilter").value = "";
            $("query").value = "";
            runSearch(true);
          },
          "quiet",
        ),
      );
    else box.append(button("＋ Write a note", openCapture, "quiet"));
    $("results").append(box);
  }
  if (!state.query && state.catalog.truncated)
    $("results").append(
      el(
        "p",
        "muted small",
        `Showing the first 500 of ${state.catalog.total} notes. Search to find any note.`,
      ),
    );
  $("contextResults").replaceChildren(
    ...context.map((n) => resultRow(n, true)),
  );
  $("contextSection").hidden = !context.length;
}
async function runSearch(push = false, preserve = "") {
  const seq = ++state.searchSeq;
  state.noteSeq++;
  noteAbort?.abort();
  searchAbort?.abort();
  searchAbort = new AbortController();
  state.query = $("query").value.trim();
  state.type = $("typeFilter").value;
  if (push) remember();
  error("");
  $("searchButton").textContent = "Finding…";
  $("results").setAttribute("aria-busy", "true");
  try {
    let notes,
      context = [];
    if (state.query) {
      const q = new URLSearchParams({
        q: state.query,
        mode: state.mode,
        type: state.type,
      });
      const data = await api("/api/search?" + q, {
        signal: searchAbort.signal,
      });
      notes = data.matches;
      context = data.context;
    } else {
      await catalog();
      notes = state.catalog.notes.filter(
        (n) => !state.type || n.type === state.type,
      );
    }
    if (seq !== state.searchSeq) return;
    $("indexStatus").textContent = state.query
      ? "Search index refreshed"
      : `${state.catalog.total} notes · refreshed just now`;
    const desktop = matchMedia("(min-width:681px)").matches;
    if (!preserve && !desktop) {
      state.selected = "";
      document.body.dataset.reading = "false";
      document.title = "Lorevell · Your working knowledge";
      remember(true);
    }
    renderResults(notes, context);
    const next = preserve || notes[0]?.id;
    if (next && (preserve || desktop))
      await readNote(next, false);
    else if (!notes.length) {
      state.selected = "";
      $("reader").replaceChildren(
        el(
          "div",
          "reader-placeholder",
          "Choose another keyword or show all notes to continue.",
        ),
      );
      document.body.dataset.reading = "false";
      document.title = "Lorevell · Your working knowledge";
      remember(true);
    }
  } catch (e) {
    if (e.name !== "AbortError" && seq === state.searchSeq)
      error(e.message + " Fix the source file if needed, then refresh.");
  } finally {
    if (seq === state.searchSeq) {
      $("searchButton").textContent = "Find a note ↗";
      $("results").removeAttribute("aria-busy");
    }
  }
}
function resolveWiki(raw, view) {
  const target = raw.split(/[|#]/)[0].trim().replace(/\.md$/, "");
  if (view.unresolved.includes(target)) return null;
  const notes = view.outgoing;
  return (
    notes.find((n) => n.id === target) ||
    notes.find((n) => n.path.replace(/\.md$/, "") === target) ||
    notes.find((n) => n.path.split("/").pop().replace(/\.md$/, "") === target)
  );
}
function inline(parent, text, view) {
  const pattern =
    /(`[^`]+`|\[\[[^\]]+\]\]|\[[^\]]+\]\([^\s)]+\)|\*\*[^*]+\*\*)/g;
  let start = 0;
  for (const match of text.matchAll(pattern)) {
    parent.append(document.createTextNode(text.slice(start, match.index)));
    const raw = match[0];
    let node;
    if (raw.startsWith("`")) node = el("code", "", raw.slice(1, -1));
    else if (raw.startsWith("**")) node = el("strong", "", raw.slice(2, -2));
    else if (raw.startsWith("[[")) {
      const value = raw.slice(2, -2),
        note = resolveWiki(value, view);
      node = el(note ? "a" : "span", "", value.split("|").pop());
      if (note) {
        node.href = urlFor(note.id);
        node.addEventListener("click", (e) => {
          if (e.metaKey || e.ctrlKey) return;
          e.preventDefault();
          readNote(note.id, true);
        });
      }
    } else {
      const parts = /^\[([^\]]+)\]\((.*)\)$/.exec(raw);
      node = el("span", "", parts[1]);
      try {
        const url = new URL(parts[2]);
        if (["https:", "http:"].includes(url.protocol)) {
          node = el("a", "", parts[1]);
          node.href = url.href;
          node.target = "_blank";
          node.rel = "noopener noreferrer";
        }
      } catch {}
    }
    parent.append(node);
    start = match.index + raw.length;
  }
  parent.append(document.createTextNode(text.slice(start)));
}
function markdown(text, view) {
  const root = el("div", "note-body");
  const lines = text.split("\n");
  let i = 0,
    skippedTitle = false;
  while (i < lines.length) {
    const line = lines[i];
    if (
      !skippedTitle &&
      line.startsWith("# ") &&
      line.slice(2).trim() === view.title
    ) {
      skippedTitle = true;
      i++;
      continue;
    }
    if (!line.trim()) {
      i++;
      continue;
    }
    const fence = /^\s*(```+|~~~+)/.exec(line);
    if (fence) {
      const marker = fence[1][0];
      const code = [];
      i++;
      while (
        i < lines.length &&
        !new RegExp("^\\s*" + marker + "{3,}").test(lines[i])
      )
        code.push(lines[i++]);
      if (i < lines.length) i++;
      const wrap = el("div", "code-wrap"),
        pre = el("pre"),
        content = code.join("\n");
      pre.append(el("code", "", content));
      wrap.append(
        pre,
        button("Copy code", () => copy(content, "Code copied")),
      );
      root.append(wrap);
      continue;
    }
    const head = /^(#{1,6})\s+(.*)/.exec(line);
    if (head) {
      const node = el("h" + Math.min(6, head[1].length + 1));
      inline(node, head[2], view);
      root.append(node);
      i++;
      continue;
    }
    if (/^\s*[-*]\s/.test(line)) {
      const list = el("ul");
      while (i < lines.length && /^\s*[-*]\s/.test(lines[i])) {
        const li = el("li");
        inline(li, lines[i++].replace(/^\s*[-*]\s/, ""), view);
        list.append(li);
      }
      root.append(list);
      continue;
    }
    const paragraph = [];
    while (
      i < lines.length &&
      lines[i].trim() &&
      !/^\s*(```|~~~|#{1,6}\s|[-*]\s)/.test(lines[i])
    )
      paragraph.push(lines[i++]);
    if (!paragraph.length) {
      paragraph.push(lines[i++]);
    }
    const p = el("p");
    inline(p, paragraph.join("\n"), view);
    root.append(p);
  }
  return root;
}
function renderNote(view) {
  const note = view.note;
  state.selected = note.id;
  $("reader").replaceChildren();
  document.body.dataset.reading = "true";
  const tools = el("div", "note-tools");
  tools.append(
    button(
      "← Notes",
      () => {
        document.body.dataset.reading = "false";
        $("query").focus();
      },
      "mobile-back",
    ),
    el("span", "file", note.path),
    button("Copy path", () => copy(view.absolute_path, "File path copied")),
    button(
      "Copy Markdown",
      () => copy(note.content, "Markdown copied"),
      "copy-main",
    ),
  );
  const inner = el("article", "note-inner"),
    meta = el("div", "note-meta");
  meta.append(el("span", "pill", note.metadata.type || "Note"));
  for (const tag of note.metadata.tags || [])
    meta.append(el("span", "", `#${tag}`));
  const heading = el("h2", "note-heading", view.title);
  heading.tabIndex = -1;
  inner.append(meta, heading, markdown(note.content, view));
  const connections = el("div", "connections");
  for (const [key, label] of [
    ["outgoing", "Linked notes"],
    ["backlinks", "Notes linking here"],
  ]) {
    const column = el("section");
    column.append(el("h3", "", label));
    if (view[key].length)
      for (const n of view[key])
        column.append(button(titleOf(n) + " ↗", () => readNote(n.id, true)));
    else
      column.append(
        el(
          "p",
          "",
          view.unindexed
            ? "Refresh the index to load connections."
            : "No linked notes.",
        ),
      );
    connections.append(column);
  }
  inner.append(connections);
  if (view.unresolved.length)
    inner.append(
      el(
        "p",
        "unresolved",
        "Unresolved links: " +
          view.unresolved.map((s) => "[[" + s + "]]").join(", "),
      ),
    );
  inner.append(el("p", "muted small", `ID · ${note.id}`));
  $("reader").append(tools, inner);
  $("reader").scrollTop = 0;
  heading.focus({ preventScroll: true });
  document.querySelectorAll(".result").forEach((n) => {
    const selected = n.dataset.id === note.id;
    n.classList.toggle("selected", selected);
    n.setAttribute("aria-pressed", String(selected));
  });
  document.title = `${view.title} · Lorevell`;
}
async function readNote(id, push) {
  const seq = ++state.noteSeq;
  noteAbort?.abort();
  noteAbort = new AbortController();
  state.selected = id;
  if (push) remember();
  try {
    const view = await api("/api/note?" + new URLSearchParams({ id }), {
      signal: noteAbort.signal,
    });
    if (seq !== state.noteSeq) return;
    renderNote(view);
    remember(true);
  } catch (e) {
    if (e.name !== "AbortError" && seq === state.noteSeq) error(e.message);
  }
}
async function copy(text, message) {
  try {
    await navigator.clipboard.writeText(text);
    toast(message);
  } catch {
    const box = el("textarea", "sr-only", text);
    document.body.append(box);
    box.select();
    const ok = document.execCommand("copy");
    box.remove();
    toast(
      ok ? message : "Copy unavailable. Select the text and copy it manually.",
    );
  }
}
function openCapture() {
  $("captureError").hidden = true;
  $("capture").showModal();
  $("noteTitle").focus();
}
$("newNote").onclick = openCapture;
$("emptyNew").onclick = openCapture;
$("cancelCapture").onclick = () => {
  if (!state.saving) $("capture").close();
};
$("capture").addEventListener("cancel", (e) => {
  if (state.saving) e.preventDefault();
});
$("captureForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  if (state.saving) return;
  state.saving = true;
  $("saveNote").disabled = true;
  $("saveNote").textContent = "Saving…";
  $("captureError").hidden = true;
  let saved;
  const title = $("noteTitle").value;
  try {
    saved = await api("/api/notes", {
      method: "POST",
      body: JSON.stringify({
        title,
        content: $("noteBody").value,
        type: $("noteType").value,
      }),
    });
  } catch (e) {
    $("captureError").textContent = e.message;
    $("captureError").hidden = false;
  } finally {
    state.saving = false;
    $("saveNote").disabled = false;
    $("saveNote").textContent = "Save to Markdown ↗";
  }
  if (!saved) return;
  $("capture").close();
  $("captureForm").reset();
  toast("Saved as Markdown");
  $("query").value = "";
  state.query = "";
  state.type = "";
  state.selected = saved.note.id;
  remember();
  try {
    await catalog();
    await runSearch(false, saved.note.id);
    if (saved.warning) error(saved.warning);
  } catch (e) {
    error(
      saved.warning ||
        `Note saved to ${saved.note.path}. Refresh needs attention: ${e.message}`,
    );
    renderNote({
      note: saved.note,
      title,
      absolute_path: saved.absolute_path,
      outgoing: [],
      backlinks: [],
      unresolved: [],
      unindexed: true,
    });
  }
});
$("searchForm").addEventListener("submit", (e) => {
  e.preventDefault();
  runSearch(true);
});
$("typeFilter").onchange = () => runSearch(true);
for (const b of document.querySelectorAll("[data-mode]"))
  b.onclick = () => {
    setMode(b.dataset.mode);
    runSearch(true, state.selected);
  };
$("refresh").onclick = async () => {
  const b = $("refresh");
  b.disabled = true;
  b.textContent = "Refreshing…";
  try {
    await api("/api/index", {
      method: "POST",
      body: JSON.stringify({ mode: state.mode }),
    });
    await catalog();
    await runSearch(false, state.selected);
    toast("Vault refreshed");
  } catch (e) {
    error(e.message);
  } finally {
    b.disabled = false;
    b.textContent = "↻ Refresh";
  }
};
document.addEventListener("keydown", (e) => {
  if (
    (e.metaKey || e.ctrlKey) &&
    e.key.toLowerCase() === "k" &&
    !$("capture").open
  ) {
    e.preventDefault();
    $("query").focus();
    $("query").select();
  }
  if (e.key === "Escape" && document.activeElement === $("query")) {
    $("query").value = "";
    runSearch(true, state.selected);
  }
});
$("results").addEventListener("keydown", (e) => {
  if (!["ArrowDown", "ArrowUp"].includes(e.key)) return;
  const items = [...$("results").querySelectorAll("button.result")],
    index = items.indexOf(document.activeElement);
  if (index < 0) return;
  e.preventDefault();
  items[
    Math.max(
      0,
      Math.min(items.length - 1, index + (e.key === "ArrowDown" ? 1 : -1)),
    )
  ].focus();
});
async function restore() {
  const p = new URLSearchParams(location.search);
  state.type = p.get("type") || "";
  $("typeFilter").value = state.type;
  $("query").value = p.get("q") || "";
  setMode(p.get("mode") === "hybrid" ? "hybrid" : "keyword");
  await runSearch(false, p.get("note") || "");
}
window.addEventListener("popstate", restore);
(async () => {
  try {
    await catalog();
    await restore();
  } catch (e) {
    error(e.message + " Fix the Markdown file, then refresh.");
    $("results").replaceChildren(
      el("p", "empty", "Your vault needs attention before it can be opened."),
    );
  }
})();
