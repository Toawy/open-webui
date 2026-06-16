<script lang="ts">
	import { getContext, tick } from 'svelte';
	import { goto } from '$app/navigation';
	import { toast } from 'svelte-sonner';

	import { user } from '$lib/stores';
	import { nameToId, formatSkillName } from '$lib/utils';
	import { updateClientScriptAccessGrants } from '$lib/apis/client-scripts';

	import CodeEditor from '$lib/components/common/CodeEditor.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import ConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';
	import ChevronLeft from '$lib/components/icons/ChevronLeft.svelte';
	import LockClosed from '$lib/components/icons/LockClosed.svelte';
	import AccessControlModal from '../common/AccessControlModal.svelte';

	const i18n = getContext('i18n');

	export let edit = false;
	export let clone = false;
	export let onSave: Function = () => {};

	export let id = '';
	export let name = '';
	export let meta: any = { description: '', manifest: {} };
	export let content = '';
	export let accessGrants: any[] = [];

	let _content = content;
	let codeEditor;
	let formElement;
	let showConfirm = false;
	let showAccessControlModal = false;

	// Auto-derive id from name on create (locked on edit)
	$: if (name && !edit && !clone && !id) {
		id = nameToId(name);
	}

	const boilerplate = `/*
title: My Script
author:
author_url:
repository_url:
funding_url:
version: 0.1.0
description: What this script does
*/
(function () {
	// Runs in your browser when Open WebUI loads. Full DOM access.
	// Self-gate by route/DOM if it should only act on certain pages.
	console.log('Hello from my script');
})();
`;

	// Parse a leading /* ... */ block comment for "key: value" metadata.
	const parseScriptFrontmatter = (text: string) => {
		const fm: Record<string, string> = {};
		const trimmed = (text ?? '').replace(/^﻿/, '').trimStart();
		if (!trimmed.startsWith('/*')) return fm;
		const end = trimmed.indexOf('*/');
		if (end === -1) return fm;
		const block = trimmed.slice(2, end);
		for (const raw of block.split('\n')) {
			const line = raw.replace(/^\s*\*?\s?/, '');
			const m = line.match(/^([a-z_]+):\s*(.*)\s*$/i);
			if (m) fm[m[1].trim()] = m[2].trim();
		}
		return fm;
	};

	const saveHandler = () => {
		const manifest = parseScriptFrontmatter(content);
		onSave({
			id,
			name,
			meta: { ...meta, manifest },
			content,
			access_grants: accessGrants
		});
	};

	const submitHandler = async () => {
		content = _content;
		await tick();
		saveHandler();
	};
</script>

<AccessControlModal
	bind:show={showAccessControlModal}
	bind:accessGrants
	accessRoles={['read', 'write']}
	share={$user?.role === 'admin' || ($user?.permissions?.sharing?.tools ?? false)}
	sharePublic={$user?.role === 'admin' || ($user?.permissions?.sharing?.public_tools ?? false)}
	shareUsers={($user?.permissions?.access_grants?.allow_users ?? true) || $user?.role === 'admin'}
	onChange={async () => {
		if (edit && id) {
			try {
				await updateClientScriptAccessGrants(localStorage.token, id, accessGrants);
				toast.success($i18n.t('Saved'));
			} catch (error) {
				toast.error(`${error}`);
			}
		}
	}}
/>

<div class="flex flex-col justify-between w-full overflow-y-auto h-full">
	<div class="mx-auto w-full md:px-0 h-full">
		<form
			bind:this={formElement}
			class="flex flex-col max-h-[100dvh] h-full"
			on:submit|preventDefault={() => {
				if (edit) {
					submitHandler();
				} else {
					showConfirm = true;
				}
			}}
		>
			<div class="flex flex-col flex-1 overflow-auto h-0 rounded-lg">
				<div class="w-full mb-2 flex flex-col gap-0.5">
					<div class="flex w-full items-center">
						<div class="shrink-0 mr-2">
							<Tooltip content={$i18n.t('Back')}>
								<button
									class="w-full text-left text-sm py-1.5 px-1 rounded-lg dark:text-gray-300 dark:hover:text-white hover:bg-black/5 dark:hover:bg-gray-850"
									aria-label={$i18n.t('Back')}
									on:click={() => goto('/workspace/scripts')}
									type="button"
								>
									<ChevronLeft strokeWidth="2.5" />
								</button>
							</Tooltip>
						</div>

						<div class="flex-1">
							<input
								class="w-full text-2xl bg-transparent outline-hidden"
								type="text"
								placeholder={$i18n.t('Script Name')}
								aria-label={$i18n.t('Script Name')}
								bind:value={name}
								required
							/>
						</div>

						<div class="self-center shrink-0">
							<button
								class="bg-gray-50 hover:bg-gray-100 text-black dark:bg-gray-850 dark:hover:bg-gray-800 dark:text-white transition px-2 py-1 rounded-full flex gap-1 items-center"
								type="button"
								on:click={() => (showAccessControlModal = true)}
							>
								<LockClosed strokeWidth="2.5" className="size-3.5" />
								<div class="text-sm font-medium shrink-0">{$i18n.t('Access')}</div>
							</button>
						</div>
					</div>

					<div class="flex gap-2 px-1 items-center">
						{#if edit}
							<div class="text-sm text-gray-500 shrink-0">{id}</div>
						{:else}
							<Tooltip className="w-full" content={$i18n.t('e.g. my_script')} placement="top-start">
								<input
									class="w-full text-sm disabled:text-gray-500 bg-transparent outline-hidden"
									type="text"
									placeholder={$i18n.t('Script ID')}
									aria-label={$i18n.t('Script ID')}
									bind:value={id}
									required
								/>
							</Tooltip>
						{/if}

						<Tooltip
							className="w-full self-center items-center flex"
							content={$i18n.t('e.g. Adds a button to the chat window')}
							placement="top-start"
						>
							<input
								class="w-full text-sm bg-transparent outline-hidden"
								type="text"
								placeholder={$i18n.t('Script Description')}
								aria-label={$i18n.t('Script Description')}
								bind:value={meta.description}
								required
							/>
						</Tooltip>
					</div>
				</div>

				<div class="mb-2 flex-1 overflow-auto h-0 rounded-lg">
					<CodeEditor
						bind:this={codeEditor}
						value={content}
						lang="javascript"
						{boilerplate}
						onChange={(e) => {
							_content = e;
							if (!edit) {
								const fm = parseScriptFrontmatter(e);
								if (fm.title && !name) {
									name = formatSkillName(fm.title);
									id = nameToId(fm.title);
								}
								if (fm.description && !meta.description) {
									meta = { ...meta, description: fm.description };
								}
							}
						}}
						onSave={async () => {
							if (formElement) formElement.requestSubmit();
						}}
					/>
				</div>

				<div class="pb-3 flex justify-between">
					<div class="flex-1 pr-3">
						<div class="text-xs text-gray-500 line-clamp-2">
							<span class="font-semibold dark:text-gray-200">{$i18n.t('Warning:')}</span>
							{$i18n.t('Scripts are a client-side scripting system with arbitrary code execution')}
							<br />—
							<span class="font-medium dark:text-gray-400"
								>{$i18n.t(`don't install random scripts from sources you don't trust.`)}</span
							>
						</div>
					</div>

					<button
						class="px-3.5 py-1.5 text-sm font-medium bg-black hover:bg-gray-900 text-white dark:bg-white dark:text-black dark:hover:bg-gray-100 transition rounded-full"
						type="submit"
					>
						{$i18n.t('Save')}
					</button>
				</div>
			</div>
		</form>
	</div>
</div>

<ConfirmDialog
	bind:show={showConfirm}
	on:confirm={() => {
		submitHandler();
	}}
>
	<div class="text-sm text-gray-500">
		<div class="bg-yellow-500/20 text-yellow-700 dark:text-yellow-200 rounded-lg px-4 py-3">
			<div>{$i18n.t('Please carefully review the following warnings:')}</div>
			<ul class="mt-1 list-disc pl-4 text-xs">
				<li>{$i18n.t('Scripts run arbitrary JavaScript in your browser.')}</li>
				<li>{$i18n.t('Do not install scripts from sources you do not fully trust.')}</li>
			</ul>
		</div>
		<div class="my-3">
			{$i18n.t(
				'I acknowledge that I have read and I understand the implications of my action. I am aware of the risks associated with executing arbitrary code and I have verified the trustworthiness of the source.'
			)}
		</div>
	</div>
</ConfirmDialog>
