<script lang="ts">
	import { onMount, getContext, onDestroy } from 'svelte';
	import { goto } from '$app/navigation';
	import { toast } from 'svelte-sonner';
	import fileSaver from 'file-saver';
	const { saveAs } = fileSaver;

	import { user, clientScripts as clientScriptsStore } from '$lib/stores';
	import { capitalizeFirstLetter } from '$lib/utils';
	import {
		getClientScriptList,
		getClientScriptById,
		createNewClientScript,
		deleteClientScriptById,
		toggleClientScriptById,
		toggleClientScriptGlobalById,
		exportClientScripts
	} from '$lib/apis/client-scripts';

	import ScriptMenu from './Scripts/ScriptMenu.svelte';
	import ViewSelector from './common/ViewSelector.svelte';
	import ManifestModal from './common/ManifestModal.svelte';
	import ConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Switch from '$lib/components/common/Switch.svelte';
	import Badge from '$lib/components/common/Badge.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import Search from '$lib/components/icons/Search.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';
	import Plus from '$lib/components/icons/Plus.svelte';
	import EllipsisHorizontal from '$lib/components/icons/EllipsisHorizontal.svelte';
	import Heart from '$lib/components/icons/Heart.svelte';
	import GarbageBin from '$lib/components/icons/GarbageBin.svelte';

	const i18n = getContext('i18n');

	let scripts = [];
	let query = '';
	let viewOption = '';
	let loaded = false;
	let shiftKey = false;

	let selectedScript = null;
	let showManifestModal = false;
	let showDeleteConfirm = false;

	let importFiles;
	let showImportConfirm = false;
	let scriptsImportInputElement: HTMLInputElement;

	$: isAdmin = $user?.role === 'admin';

	$: filteredItems = (scripts ?? []).filter((s) => {
		if (query === '' && viewOption === '') return true;
		const q = query.toLowerCase();
		const matchesQuery =
			(s.name || '').toLowerCase().includes(q) ||
			(s.id || '').toLowerCase().includes(q) ||
			(s.user?.name || '').toLowerCase().includes(q) ||
			(s.user?.email || '').toLowerCase().includes(q);
		const matchesView =
			viewOption === '' ||
			(viewOption === 'created' && s.user_id === $user?.id) ||
			(viewOption === 'shared' && s.user_id !== $user?.id);
		return matchesQuery && matchesView;
	});

	const init = async () => {
		scripts = (await getClientScriptList(localStorage.token)) ?? [];
		clientScriptsStore.set(scripts);
		loaded = true;
	};

	const deleteHandler = async (script) => {
		const res = await deleteClientScriptById(localStorage.token, script.id).catch((e) => {
			toast.error(`${e}`);
			return null;
		});
		if (res) {
			toast.success($i18n.t('Script deleted successfully'));
			await init();
		}
	};

	const cloneHandler = async (script) => {
		const _script = await getClientScriptById(localStorage.token, script.id).catch((e) => {
			toast.error(`${e}`);
			return null;
		});
		if (_script) {
			sessionStorage.script = JSON.stringify({
				..._script,
				id: `${_script.id}_clone`,
				name: `${_script.name} (Clone)`
			});
			goto('/workspace/scripts/create');
		}
	};

	const exportHandler = async (script) => {
		const _script = await getClientScriptById(localStorage.token, script.id).catch((e) => {
			toast.error(`${e}`);
			return null;
		});
		if (_script) {
			const blob = new Blob([JSON.stringify([_script])], { type: 'application/json' });
			saveAs(blob, `script-${_script.id}-export-${Date.now()}.json`);
		}
	};

	const toggleHandler = async (script) => {
		const res = await toggleClientScriptById(localStorage.token, script.id).catch((e) => {
			toast.error(`${e}`);
			return null;
		});
		if (!res) {
			script.is_active = !script.is_active;
			scripts = scripts;
			return;
		}
		toast.success(
			res.is_active
				? $i18n.t('Script enabled — reload to run it')
				: $i18n.t('Script disabled')
		);
	};

	const toggleGlobalHandler = async (script) => {
		const res = await toggleClientScriptGlobalById(localStorage.token, script.id).catch((e) => {
			toast.error(`${e}`);
			return null;
		});
		if (!res) {
			script.is_global = !script.is_global;
			scripts = scripts;
			return;
		}
		toast.success(
			res.is_global
				? $i18n.t('Script is now global — it runs for every user')
				: $i18n.t('Script is no longer global')
		);
		await init();
	};

	const onKeyDown = (e) => {
		if (e.key === 'Shift') shiftKey = true;
	};
	const onKeyUp = (e) => {
		if (e.key === 'Shift') shiftKey = false;
	};
	const onBlur = () => {
		shiftKey = false;
	};

	onMount(async () => {
		await init();
		window.addEventListener('keydown', onKeyDown);
		window.addEventListener('keyup', onKeyUp);
		window.addEventListener('blur', onBlur);
	});

	onDestroy(() => {
		window.removeEventListener('keydown', onKeyDown);
		window.removeEventListener('keyup', onKeyUp);
		window.removeEventListener('blur', onBlur);
	});
</script>

{#if loaded}
	<div class="flex flex-col gap-1 my-1.5">
		<div class="flex justify-between items-center">
			<div class="flex items-center md:self-center text-xl font-medium px-0.5 gap-2 shrink-0">
				<div>{$i18n.t('Scripts')}</div>
				<div class="text-lg font-medium text-gray-500 dark:text-gray-500">{filteredItems.length}</div>
			</div>

			<div class="flex w-full justify-end gap-1.5">
				<button
					class="flex text-xs items-center space-x-1 px-3 py-1.5 rounded-xl bg-gray-50 hover:bg-gray-100 dark:bg-gray-850 dark:hover:bg-gray-800 dark:text-gray-200 transition"
					on:click={() => scriptsImportInputElement.click()}
				>
					<div class="self-center font-medium line-clamp-1">{$i18n.t('Import')}</div>
				</button>

				{#if scripts.length}
					<button
						class="flex text-xs items-center space-x-1 px-3 py-1.5 rounded-xl bg-gray-50 hover:bg-gray-100 dark:bg-gray-850 dark:hover:bg-gray-800 dark:text-gray-200 transition"
						on:click={async () => {
							const _scripts = await exportClientScripts(localStorage.token).catch((e) => {
								toast.error(`${e}`);
								return null;
							});
							if (_scripts) {
								const blob = new Blob([JSON.stringify(_scripts)], { type: 'application/json' });
								saveAs(blob, `scripts-export-${Date.now()}.json`);
							}
						}}
					>
						<div class="self-center font-medium line-clamp-1">{$i18n.t('Export')}</div>
					</button>
				{/if}

				<a
					class="px-2 py-1.5 rounded-xl bg-black text-white dark:bg-white dark:text-black transition font-medium text-sm flex items-center"
					href="/workspace/scripts/create"
				>
					<Plus className="size-3" strokeWidth="2.5" />
					<div class="hidden md:block md:ml-1 text-xs">{$i18n.t('New Script')}</div>
				</a>
			</div>
		</div>
	</div>

	<div class="flex w-full space-x-2 py-0.5 px-3.5 pb-2">
		<div class="flex flex-1">
			<div class="self-center ml-1 mr-3">
				<Search className="size-3.5" />
			</div>
			<input
				class="w-full text-sm pr-4 py-1 rounded-r-xl outline-hidden bg-transparent"
				bind:value={query}
				aria-label={$i18n.t('Search Scripts')}
				placeholder={$i18n.t('Search Scripts')}
			/>
			{#if query}
				<div class="self-center pl-1.5 translate-y-[0.5px] rounded-l-xl bg-transparent">
					<button
						class="p-0.5 rounded-full hover:bg-gray-100 dark:hover:bg-gray-900 transition"
						aria-label={$i18n.t('Clear search')}
						on:click={() => (query = '')}
					>
						<XMark className="size-3" strokeWidth="2" />
					</button>
				</div>
			{/if}
		</div>
	</div>

	<div class="px-3 flex w-full bg-transparent overflow-x-auto scrollbar-none -mx-1">
		<div class="flex gap-0.5 w-fit text-center text-sm rounded-full bg-transparent px-1.5 whitespace-nowrap">
			<ViewSelector
				bind:value={viewOption}
				onChange={(value) => {
					localStorage.workspaceViewOption = value;
				}}
			/>
		</div>
	</div>

	{#if filteredItems.length !== 0}
		<div class="my-2 gap-2 grid px-3 lg:grid-cols-2">
			{#each filteredItems as script (script.id)}
				<Tooltip content={script?.meta?.description ?? script?.id}>
					<div
						class="flex space-x-4 text-left w-full px-3 py-2.5 transition rounded-2xl {script.write_access
							? 'cursor-pointer dark:hover:bg-gray-850/50 hover:bg-gray-50'
							: 'cursor-not-allowed opacity-60'}"
					>
						{#if script.write_access}
							<a
								class="flex flex-1 space-x-3.5 cursor-pointer w-full"
								href={`/workspace/scripts/edit?id=${encodeURIComponent(script.id)}`}
							>
								<div class="flex items-center text-left">
									<div class="flex-1 self-center">
										<Tooltip content={script.id} placement="top-start">
											<div class="flex items-center gap-2">
												<div class="line-clamp-1 text-sm">{script.name}</div>
												{#if script?.meta?.manifest?.version}
													<div class="text-gray-500 text-xs font-medium shrink-0">
														v{script?.meta?.manifest?.version ?? ''}
													</div>
												{/if}
												{#if script.is_global}
													<div class="text-[10px] uppercase tracking-wide text-blue-600 dark:text-blue-400 shrink-0">
														{$i18n.t('Global')}
													</div>
												{/if}
											</div>
										</Tooltip>
										<div class="px-0.5">
											<div class="text-xs text-gray-500 shrink-0">
												{$i18n.t('By {{name}}', {
													name: capitalizeFirstLetter(
														script?.user?.name ?? script?.user?.email ?? $i18n.t('Deleted User')
													)
												})}
											</div>
										</div>
									</div>
								</div>
							</a>
						{:else}
							<div class="flex flex-1 space-x-3.5 w-full">
								<div class="flex items-center text-left w-full">
									<div class="flex-1 self-center w-full">
										<div class="flex items-center justify-between w-full gap-2">
											<Tooltip content={script.id} placement="top-start">
												<div class="flex items-center gap-2">
													<div class="line-clamp-1 text-sm">{script.name}</div>
													{#if script?.meta?.manifest?.version}
														<div class="text-gray-500 text-xs font-medium shrink-0">
															v{script?.meta?.manifest?.version ?? ''}
														</div>
													{/if}
												</div>
											</Tooltip>
											<Badge type="muted" content={$i18n.t('Read Only')} />
										</div>
										<div class="px-0.5">
											<div class="text-xs text-gray-500 shrink-0">
												{$i18n.t('By {{name}}', {
													name: capitalizeFirstLetter(
														script?.user?.name ?? script?.user?.email ?? $i18n.t('Deleted User')
													)
												})}
											</div>
										</div>
									</div>
								</div>
							</div>
						{/if}

						{#if script.write_access}
							<div class="flex flex-row gap-0.5 self-center items-center">
								{#if shiftKey}
									<Tooltip content={$i18n.t('Delete')}>
										<button
											class="self-center w-fit text-sm px-2 py-2 dark:text-gray-300 dark:hover:text-white hover:bg-black/5 dark:hover:bg-white/5 rounded-xl"
											type="button"
											aria-label={$i18n.t('Delete')}
											on:click|preventDefault={() => {
												selectedScript = script;
												showDeleteConfirm = true;
											}}
										>
											<GarbageBin />
										</button>
									</Tooltip>
								{:else}
									{#if script?.meta?.manifest?.funding_url ?? false}
										<Tooltip content={$i18n.t('Support')}>
											<button
												class="self-center w-fit text-sm px-2 py-2 dark:text-gray-300 dark:hover:text-white hover:bg-black/5 dark:hover:bg-white/5 rounded-xl"
												type="button"
												aria-label={$i18n.t('Support')}
												on:click|preventDefault={() => {
													selectedScript = script;
													showManifestModal = true;
												}}
											>
												<Heart />
											</button>
										</Tooltip>
									{/if}

									{#if isAdmin}
										<Tooltip content={$i18n.t('Run for all users (global)')}>
											<div class="flex items-center gap-1 px-1">
												<span class="text-[10px] text-gray-400">{$i18n.t('Global')}</span>
												<Switch
													bind:state={script.is_global}
													on:change={() => toggleGlobalHandler(script)}
												/>
											</div>
										</Tooltip>
									{/if}

									<ScriptMenu
										editHandler={() =>
											goto(`/workspace/scripts/edit?id=${encodeURIComponent(script.id)}`)}
										cloneHandler={() => cloneHandler(script)}
										exportHandler={() => exportHandler(script)}
										deleteHandler={() => {
											selectedScript = script;
											showDeleteConfirm = true;
										}}
									>
										<button
											class="self-center w-fit text-sm p-1.5 dark:text-gray-300 dark:hover:text-white hover:bg-black/5 dark:hover:bg-white/5 rounded-xl"
											type="button"
											on:click|preventDefault
										>
											<EllipsisHorizontal className="size-5" />
										</button>
									</ScriptMenu>

									<Tooltip content={script.is_active ? $i18n.t('Enabled') : $i18n.t('Disabled')}>
										<Switch bind:state={script.is_active} on:change={() => toggleHandler(script)} />
									</Tooltip>
								{/if}
							</div>
						{:else if script?.meta?.manifest?.funding_url ?? false}
							<div class="flex flex-row gap-0.5 self-center">
								<Tooltip content={$i18n.t('Support')}>
									<button
										class="self-center w-fit text-sm px-2 py-2 dark:text-gray-300 hover:bg-black/5 dark:hover:bg-white/5 rounded-xl"
										type="button"
										on:click|preventDefault={() => {
											selectedScript = script;
											showManifestModal = true;
										}}
									>
										<Heart />
									</button>
								</Tooltip>
							</div>
						{/if}
					</div>
				</Tooltip>
			{/each}
		</div>
	{:else}
		<div class="w-full h-full flex flex-col justify-center items-center my-16 mb-24">
			<div class="max-w-md text-center">
				<div class="text-3xl mb-3">😕</div>
				<div class="text-lg font-medium mb-1">{$i18n.t('No scripts found')}</div>
				<div class="text-gray-500 text-center text-xs">
					{$i18n.t('Try adjusting your search or filter to find what you are looking for.')}
				</div>
			</div>
		</div>
	{/if}
{:else}
	<div class="w-full h-full flex justify-center items-center">
		<Spinner className="size-5" />
	</div>
{/if}

<input
	bind:this={scriptsImportInputElement}
	bind:files={importFiles}
	type="file"
	accept=".json"
	hidden
	on:change={() => {
		showImportConfirm = true;
	}}
/>

<ManifestModal bind:show={showManifestModal} manifest={selectedScript?.meta?.manifest ?? {}} />

<ConfirmDialog
	bind:show={showDeleteConfirm}
	title={$i18n.t('Delete script?')}
	on:confirm={() => {
		if (selectedScript) deleteHandler(selectedScript);
	}}
>
	<div class="text-sm text-gray-500">
		{$i18n.t('This will delete')}
		<span class="font-semibold">{selectedScript?.name}</span>. {$i18n.t('This action cannot be undone.')}
	</div>
</ConfirmDialog>

<ConfirmDialog
	bind:show={showImportConfirm}
	on:confirm={() => {
		const reader = new FileReader();
		reader.onload = async (event) => {
			const _scripts = JSON.parse(event.target.result);
			for (const script of _scripts) {
				await createNewClientScript(localStorage.token, script).catch((e) => {
					toast.error(`${e}`);
					return null;
				});
			}
			toast.success($i18n.t('Scripts imported successfully'));
			await init();
			importFiles = null;
			scriptsImportInputElement.value = '';
		};
		reader.readAsText(importFiles[0]);
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
