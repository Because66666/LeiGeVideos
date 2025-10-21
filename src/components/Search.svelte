<script lang="ts">
import I18nKey from "@i18n/i18nKey";
import { i18n } from "@i18n/translation";
import Icon from "@iconify/svelte";
import { url } from "@utils/url-utils.ts";
import { onMount } from "svelte";
import Fuse from "fuse.js";

let keywordDesktop = "";
let keywordMobile = "";
let result: { url: string; meta: { title: string }; excerpt: string }[] = [];

let search = (keyword: string, isDesktop: boolean) => {};

let fuse: Fuse<any> | null = null;
let indexItems: any[] = [];

async function initFuse() {
    if (fuse) return;
    try {
        const res = await fetch(url('/search-index.json'));
        const data = await res.json();
        indexItems = data.items || [];
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

    // Prefer match from Fuse
    const m = matches && matches.find((mm) => mm.key === 'content' || mm.key === 'description' || mm.key === 'title');
    if (m && Array.isArray(m.indices) && m.indices.length > 0) {
        const [s, e] = m.indices[0];
        const start = Math.max(0, s - 30);
        const end = Math.min(text.length, e + 30);
        const slice = text.slice(start, end);
        const target = text.slice(s, e + 1);
        return slice.replace(target, `<mark>${target}</mark>`);
    }

    // Fallback to simple substring highlight
    const pos = lowerText.indexOf(lowerKey);
    if (pos >= 0) {
        const start = Math.max(0, pos - 30);
        const end = Math.min(text.length, pos + keyword.length + 30);
        const slice = text.slice(start, end);
        return slice.replace(text.slice(pos, pos + keyword.length), `<mark>${text.slice(pos, pos + keyword.length)}</mark>`);
    }

    return text.slice(0, 80);
}

onMount(() => {
    search = async (keyword: string, isDesktop: boolean) => {
        let panel = document.getElementById("search-panel");
        if (!panel) return;

        if (!keyword && isDesktop) {
            panel.classList.add("float-panel-closed");
            result = [];
            return;
        }

        await initFuse();

        let arr: any[] = [];
        if (fuse && keyword) {
            try {
                const ret = fuse.search(keyword);
                arr = ret.slice(0, 20).map(({ item, matches }) => ({
                    url: item.url,
                    meta: { title: item.title },
                    excerpt: buildExcerpt(item.content || item.description || "", keyword, matches),
                }));
            } catch (err) {
                console.warn("Fuse search failed:", err);
                arr = [];
            }
        }

        if (!arr.length && isDesktop) {
            panel.classList.add("float-panel-closed");
            result = [];
            return;
        }

        if (isDesktop) {
            panel.classList.remove("float-panel-closed");
        }
        result = arr as any;
    };
});

const togglePanel = () => {
    let panel = document.getElementById("search-panel");
    panel?.classList.toggle("float-panel-closed");
};

$: search(keywordDesktop, true);
$: search(keywordMobile, false);
</script>

<!-- search bar for desktop view -->
<div id="search-bar" class="hidden lg:flex transition-all items-center h-11 mr-2 rounded-lg
      bg-black/[0.04] hover:bg-black/[0.06] focus-within:bg-black/[0.06]
      dark:bg-white/5 dark:hover:bg-white/10 dark:focus-within:bg-white/10
">
    <Icon icon="material-symbols:search" class="absolute text-[1.25rem] pointer-events-none ml-3 transition my-auto text-black/30 dark:text-white/30"></Icon>
    <input placeholder="{i18n(I18nKey.search)}" bind:value={keywordDesktop} on:focus={() => search(keywordDesktop, true)}
           class="transition-all pl-10 text-sm bg-transparent outline-0
         h-full w-40 active:w-60 focus:w-60 text-black/50 dark:text-white/50"
    >
</div>

<!-- toggle btn for phone/tablet view -->
<button on:click={togglePanel} aria-label="Search Panel" id="search-switch"
        class="btn-plain scale-animation lg:!hidden rounded-lg w-11 h-11 active:scale-90">
    <Icon icon="material-symbols:search" class="text-[1.25rem]"></Icon>
</button>

<!-- search panel -->
<div id="search-panel" class="float-panel float-panel-closed search-panel absolute md:w-[30rem]
top-20 left-4 md:left-[unset] right-4 shadow-2xl rounded-2xl p-2 overflow-y-auto max-h-[70vh]">

    <!-- search bar inside panel for phone/tablet -->
    <div id="search-bar-inside" class="flex relative lg:hidden transition-all items-center h-11 rounded-xl
      bg-black/[0.04] hover:bg-black/[0.06] focus-within:bg-black/[0.06]
      dark:bg-white/5 dark:hover:bg-white/10 dark:focus-within:bg-white/10
  ">
        <Icon icon="material-symbols:search" class="absolute text-[1.25rem] pointer-events-none ml-3 transition my-auto text-black/30 dark:text-white/30"></Icon>
        <input placeholder="Search" bind:value={keywordMobile}
               class="pl-10 absolute inset-0 text-sm bg-transparent outline-0
               focus:w-60 text-black/50 dark:text-white/50"
        >
    </div>

    <!-- search results -->
    {#each result as item}
        <a href={item.url}
           class="transition first-of-type:mt-2 lg:first-of-type:mt-0 group block
       rounded-xl text-lg px-3 py-2 hover:bg-[var(--btn-plain-bg-hover)] active:bg-[var(--btn-plain-bg-active)]">
            <div class="transition text-90 inline-flex font-bold group-hover:text-[var(--primary)]">
                {item.meta.title}<Icon icon="fa6-solid:chevron-right" class="transition text-[0.75rem] translate-x-1 my-auto text-[var(--primary)]"></Icon>
            </div>
            <div class="transition text-sm text-50">
                {@html item.excerpt}
            </div>
        </a>
    {/each}
</div>

<style>
  input:focus {
    outline: 0;
  }
</style>
