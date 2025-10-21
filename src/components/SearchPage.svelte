<script lang="ts">
import Icon from "@iconify/svelte";
import { url } from "@utils/url-utils";
import Fuse from "fuse.js";
import { onMount } from "svelte";

interface SearchIndexItem {
	url: string;
	title: string;
	description?: string;
	content?: string;
	tags?: string[];
	category?: string;
	published?: string;
}

let keyword = "";
let results: {
	url: string;
	title: string;
	excerpt: string;
	published: string;
	category?: string;
}[] = [];
let fuse: any = null;
let indexItems: SearchIndexItem[] = [];

async function initFuse() {
	if (fuse) return;
	try {
		const res = await fetch(url("/search-index.json"));
		const data = await res.json();
		indexItems = (data.items || []) as SearchIndexItem[];
		fuse = new Fuse(indexItems, {
			keys: ["title", "description", "content", "tags", "category"],
			isCaseSensitive: false,
			includeMatches: true,
			includeScore: true,
			shouldSort: true,
			ignoreLocation: true,
			threshold: 0.3,
			minMatchCharLength: 1,
		});
	} catch (e) {
		console.warn("Search index load failed:", e);
	}
}

function buildExcerpt(text: string, keyword: string, matches?: any[]): string {
	if (!text) return "";
	const lowerText = text.toLowerCase();
	const lowerKey = keyword.toLowerCase();

	// 仅在 content/description 命中时使用 Fuse 提供的索引，避免 title 命中导致错位
	const m =
		matches &&
		matches.find((mm: any) => mm.key === "content" || mm.key === "description");
	if (m && Array.isArray(m.indices) && m.indices.length > 0) {
		const [s, e] = m.indices[0];
		const start = Math.max(0, s - 30);
		const end = Math.min(text.length, e + 30);
		const slice = text.slice(start, end);
		const target = text.slice(s, e + 1);
		return slice.replace(target, `<mark>${target}</mark>`);
	}

	// Fallback: 简单子串高亮（仅在 text 中找到关键字时）
	const pos = lowerText.indexOf(lowerKey);
	if (pos >= 0) {
		const start = Math.max(0, pos - 30);
		const end = Math.min(text.length, pos + keyword.length + 30);
		const slice = text.slice(start, end);
		return slice.replace(
			text.slice(pos, pos + keyword.length),
			`<mark>${text.slice(pos, pos + keyword.length)}</mark>`,
		);
	}

	return text.slice(0, 80);
}

async function doSearch() {
	if (!keyword) {
		results = [];
		return;
	}
	await initFuse();
	if (!fuse) {
		results = [];
		return;
	}
	try {
		const ret = fuse.search(keyword);
		results = ret.map(({ item, matches }: any) => {
			const baseText = item.content || item.description || "";
			const excerpt = buildExcerpt(baseText, keyword, matches);
			return {
				url: item.url,
				title: item.title,
				excerpt,
				published: item.published
					? new Date(item.published).toLocaleDateString()
					: "",
				category: item.category || "",
			};
		});
	} catch (e) {
		console.warn("Fuse search failed:", e);
		results = [];
	}
}

onMount(async () => {
	const params = new URLSearchParams(window.location.search);
	const q = params.get("q");
	if (q) {
		keyword = q;
		await initFuse();
		await doSearch();
	} else {
		await initFuse();
	}
});

$: doSearch();
</script>

<!-- Search bar -->
<!-- <div id="search-bar-page" class="transition-all items-center h-11 rounded-lg mb-4
      bg-black/[0.04] hover:bg-black/[0.06] focus-within:bg-black/[0.06]
      dark:bg-white/5 dark:hover:bg-white/10 dark:focus-within:bg-white/10
      flex w-full">
  <Icon icon="material-symbols:search" class="absolute text-[1.25rem] pointer-events-none ml-3 transition my-auto text-black/30 dark:text-white/30"></Icon>
  <input placeholder="Search" bind:value={keyword}
         class="transition-all pl-10 text-sm bg-transparent outline-0 h-full w-full text-black/50 dark:text-white/50"
  >
</div> -->

<!-- Results wrapper mimicking PostPage list container -->
<div class="transition flex flex-col rounded-[var(--radius-large)] bg-[var(--card-bg)] py-1 md:py-0 md:bg-transparent md:gap-4 mb-4">
  {#if results.length === 0}
    <div class="text-center text-70 py-8">等待搜索</div>
  {:else}
    {#each results as item, i}
      <div class="card-base flex flex-col-reverse md:flex-col w-full rounded-[var(--radius-large)] overflow-hidden relative onload-animation"
           style={`animation-delay: calc(var(--content-delay) + ${i * 50}ms);`}>
        <div class="pl-6 md:pl-9 pr-6 md:pr-2 pt-6 md:pt-7 pb-6 relative w-full md:w-[calc(100%_-_52px_-_12px)]">
          <a href={item.url}
             class="transition group w-full block font-bold mb-3 text-3xl text-90 hover:text-[var(--primary)] dark:hover:text-[var(--primary)] active:text-[var(--title-active)] dark:active:text-[var(--title-active)] before:w-1 before:h-5 before:rounded-md before:bg-[var(--primary)] before:absolute before:top-[35px] before:left-[18px] before:hidden md:before:block">
            {item.title}
            <Icon class="inline text-[2rem] text-[var(--primary)] md:hidden translate-y-0.5 absolute" icon="material-symbols:chevron-right-rounded" ></Icon>
            <Icon class="text-[var(--primary)] text-[2rem] transition hidden md:inline absolute translate-y-0.5 opacity-0 group-hover:opacity-100 -translate-x-1 group-hover:translate-x-0" icon="material-symbols:chevron-right-rounded"></Icon>
          </a>
          <div class="transition text-75 mb-3.5 pr-4">
            {@html item.excerpt}
          </div>
          <div class="text-sm text-black/30 dark:text-white/30 flex gap-4 transition">
            {#if item.published}<div>{item.published}</div>{/if}
            {#if item.published && item.category}<div>|</div>{/if}
            {#if item.category}<div>{item.category}</div>{/if}
          </div>
        </div>
      </div>
      <div class="transition border-t-[1px] border-dashed mx-6 border-black/10 dark:border-white/[0.15] last:border-t-0 md:hidden"></div>
    {/each}
  {/if}
</div>

<style>
  input:focus { outline: 0; }
</style>