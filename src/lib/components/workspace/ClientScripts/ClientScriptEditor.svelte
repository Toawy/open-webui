<script lang="ts">
	import { onMount, getContext } from 'svelte';
	import { goto } from '$app/navigation';
	import { page } from '$app/stores';
	import { toast } from 'svelte-sonner';

	import {
		createNewClientScript,
		getClientScriptById,
		updateClientScriptById
	} from '$lib/apis/client-scripts';

	import CodeEditor from '$lib/components/common/CodeEditor.svelte';

	export let edit = false;

	const i18n = getContext('i18n');

	let codeEditor;

	let id = '';
	let name = '';
	let description = '';
	let content = '';
	let saving = false;
	let loaded = false;

	const boilerplate = `/*
 * Client Script — runs in your browser when Open WebUI loads.
 * It has full access to the page DOM (same as DevTools or a userscript).
 */
(function () {
	console.log('Hello from my client script');
})();
`;

	const submitHandler = async () => {
		if (saving) return;

		if (!name.trim()) {
			toast.error($i18n.t('Please give your client script a name.'));
			return;
		}

		saving = true;
		const form = {
			name: name.trim(),
			content,
			meta: { description: description.trim() }
		};

		let res;
		if (edit) {
			res = await updateClientScriptById(localStorage.token, id, form).catch((e) => {
				toast.error(`${e}`);
				return null;
			});
		} else {
			res = await createNewClientScript(localStorage.token, form).catch((e) => {
				toast.error(`${e}`);
				return null;
			});
		}

		saving = false;

		if (res) {
			toast.success(edit ? $i18n.t('Client script updated') : $i18n.t('Client script created'));
			await goto('/workspace/client-scripts');
		}
	};

	onMount(async () => {
		if (edit) {
			id = $page.url.searchParams.get('id') ?? '';
			const script = await getClientScriptById(localStorage.token, id).catch((e) => {
				toast.error(`${e}`);
				return null;
			});

			if (!script) {
				await goto('/workspace/client-scripts');
				return;
			}

			name = script.name ?? '';
			description = script?.meta?.description ?? '';
			content = script.content ?? '';
		}
		loaded = true;
	});
</script>

{#if loaded}
	<form
		class="flex flex-col h-full gap-2 my-1.5"
		on:submit|preventDefault={submitHandler}
	>
		<div class="flex justify-between items-center">
			<div class="text-xl font-medium px-0.5">
				{edit ? $i18n.t('Edit Client Script') : $i18n.t('New Client Script')}
			</div>

			<div class="flex gap-1">
				<a
					class="text-sm px-3 py-1.5 rounded-xl hover:bg-black/5 dark:hover:bg-white/5 transition"
					href="/workspace/client-scripts"
				>
					{$i18n.t('Cancel')}
				</a>
				<button
					class="text-sm px-3 py-1.5 rounded-xl bg-black hover:bg-gray-900 text-white dark:bg-white dark:hover:bg-gray-100 dark:text-black transition disabled:opacity-50"
					type="submit"
					disabled={saving}
				>
					{$i18n.t('Save')}
				</button>
			</div>
		</div>

		<div class="flex flex-col gap-2 mt-1">
			<input
				class="w-full text-sm bg-transparent outline-none border border-gray-100 dark:border-gray-850 rounded-xl px-3 py-1.5"
				placeholder={$i18n.t('Name')}
				bind:value={name}
				required
			/>
			<input
				class="w-full text-sm bg-transparent outline-none border border-gray-100 dark:border-gray-850 rounded-xl px-3 py-1.5"
				placeholder={$i18n.t('Description (optional)')}
				bind:value={description}
			/>
		</div>

		<div class="flex-1 min-h-[50vh] border border-gray-100 dark:border-gray-850 rounded-xl overflow-hidden mt-1">
			<CodeEditor
				bind:this={codeEditor}
				value={content}
				lang="javascript"
				{boilerplate}
				onChange={(e) => {
					content = e;
				}}
				onSave={() => submitHandler()}
			/>
		</div>

		<div class="text-xs text-gray-500 dark:text-gray-400 px-0.5 mt-1">
			{$i18n.t(
				'This code runs in your browser only. Treat scripts from others the same as any userscript.'
			)}
		</div>
	</form>
{/if}
