import { getCollection } from "astro:content";
import { getPostUrlBySlug } from "@utils/url-utils";
import type { APIRoute } from "astro";

function stripMarkdown(md: string): string {
	return md
		.replace(/```[\s\S]*?```/g, " ") // code blocks
		.replace(/`[^`]*`/g, " ") // inline code
		.replace(/!\[[^\]]*\]\([^\)]+\)/g, " ") // images
		.replace(/\[[^\]]*\]\([^\)]+\)/g, " ") // links
		.replace(/[#>*_\-]{1,}/g, " ")
		.replace(/\s{2,}/g, " ")
		.trim();
}

export const GET: APIRoute = async () => {
	const posts = await getCollection("posts", ({ data }) => {
		return import.meta.env.PROD ? data.draft !== true : true;
	});

	const items = posts.map((entry) => {
		const raw = entry.body ?? "";
		const content = stripMarkdown(raw);
		return {
			url: getPostUrlBySlug(entry.slug),
			title: entry.data.title,
			description: entry.data.description ?? "",
			tags: entry.data.tags ?? [],
			category: entry.data.category ?? "",
			content: content.slice(0, 2000),
			meta: { title: entry.data.title },
			excerpt: content.slice(0, 120),
			published: entry.data.published,
		};
	});

	return new Response(JSON.stringify({ items }), {
		headers: { "Content-Type": "application/json" },
	});
};
