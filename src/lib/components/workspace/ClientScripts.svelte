<script lang="ts">
	import { onMount, getContext } from 'svelte';
	import { toast } from 'svelte-sonner';

	import { user, clientScripts as clientScriptsStore } from '$lib/stores';
	import {
		getClientScripts,
		getGlobalClientScripts,
		toggleClientScriptById,
		toggleClientScriptGlobalById,
		deleteClientScriptById
	} from '$lib/apis/client-scripts';

	import Switch from '$lib/components/common/Switch.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';

	const i18n = getContext('i18n');

	let scripts = [];
	let globalScripts = [];
	let query = '';
	let loaded = false;

	$: isAdmin = $user?.role === 'admin';

	$: filtered = (scripts ?? []).filter((s) =>
		query === '' ? true : (s?.name ?? '').toLowerCase().includes(query.toLowerCase())
	);

	const init = async () => {
		scripts = (await getClientScripts(localStorage.token)) ?? [];
		clientScriptsStore.set(scripts);
		if ($user?.role === 'admin') {
			globalScripts = (await getGlobalClientScripts(localStorage.token)) ?? [];
		}
		loaded = true;
	};

	const toggleHandler = async (script) => {
		// bind:state has already flipped script.is_active optimistically.
		const res = await toggleClientScriptById(localStorage.token, script.id).catch((e) => {
			toast.error(`${e}`);
			return null;
		});

		if (!res) {
			script.is_active = !script.is_active; // revert on failure
			scripts = scripts;
			globalScripts = globalScripts;
			return;
		}

		toast.success(
			res.is_active
				? $i18n.t('Client script enabled — reload to run it')
				: $i18n.t('Client script disabled')
		);
	};

	const toggleGlobalHandler = async (script) => {
		// bind:state has already flipped script.is_global optimistically.
		const res = await toggleClientScriptGlobalById(localStorage.token, script.id).catch((e) => {
			toast.error(`${e}`);
			return null;
		});

		if (!res) {
			script.is_global = !script.is_global; // revert on failure
			scripts = scripts;
			globalScripts = globalScripts;
			return;
		}

		toast.success(
			res.is_global
				? $i18n.t('Script is now global — it runs for every user')
				: $i18n.t('Script is no longer global')
		);
		await init(); // refetch own + global lists to stay consistent
	};

	const deleteHandler = async (script) => {
		if (!confirm($i18n.t('Delete this client script? This cannot be undone.'))) return;

		const res = await deleteClientScriptById(localStorage.token, script.id).catch((e) => {
			toast.error(`${e}`);
			return null;
		});

		if (res) {
			toast.success($i18n.t('Client script deleted'));
			await init();
		}
	};

	onMount(init);
</script>

<div class="flex flex-col gap-1 my-1.5">
	<div class="flex justify-between items-center">
		<div class="flex items-center md:self-center text-xl font-medium px-0.5">
			{$i18n.t('Client Scripts')}
			<div class="flex self-center w-[1px] h-6 mx-2.5 bg-gray-50 dark:bg-gray-850" />
			<span class="text-lg font-medium text-gray-500 dark:text-gray-300">{filtered.length}</span>
		</div>

		<a
			class="flex items-center gap-1 text-sm px-3 py-1.5 rounded-xl bg-black hover:bg-gray-900 text-white dark:bg-white dark:hover:bg-gray-100 dark:text-black transition"
			href="/workspace/client-scripts/create"
		>
			{$i18n.t('Create New')}
		</a>
	</div>

	<div class="text-xs text-gray-500 dark:text-gray-400 px-0.5">
		{$i18n.t(
			'JavaScript that runs in your own browser when Open WebUI loads. These run only for you.'
		)}
	</div>
</div>

<div class="my-2">
	<input
		class="w-full text-sm bg-transparent outline-none border border-gray-100 dark:border-gray-850 rounded-xl px-3 py-1.5"
		placeholder={$i18n.t('Search Client Scripts')}
		bind:value={query}
	/>
</div>

{#if loaded}
	{#if filtered.length > 0}
		<div class="my-2 gap-1 lg:gap-2 grid lg:grid-cols-2">
			{#each filtered as script (script.id)}
				<div
					class="flex space-x-4 cursor-pointer w-full px-2 py-2 dark:hover:bg-white/5 hover:bg-black/5 rounded-xl"
				>
					<a
						class="flex flex-1 flex-col cursor-pointer w-full"
						href={`/workspace/client-scripts/edit?id=${encodeURIComponent(script.id)}`}
					>
						<div class="font-medium line-clamp-1">
							{script.name}
							{#if script.is_global}
								<span
									class="ml-1 text-[10px] uppercase tracking-wide text-blue-600 dark:text-blue-400"
									>{$i18n.t('Global')}</span
								>
							{/if}
						</div>
						<div class="text-xs text-gray-500 dark:text-gray-400 line-clamp-1">
							{script?.meta?.description ?? ''}
						</div>
					</a>

					<div class="flex flex-row items-center gap-2 self-center">
						{#if isAdmin}
							<Tooltip content={$i18n.t('Run for all users (global)')}>
								<div class="flex items-center gap-1">
									<span class="text-[10px] text-gray-400">{$i18n.t('Global')}</span>
									<Switch
										bind:state={script.is_global}
										on:change={() => toggleGlobalHandler(script)}
									/>
								</div>
							</Tooltip>
						{/if}

						<Tooltip content={$i18n.t('Delete')}>
							<button
								class="self-center w-fit text-sm px-2 py-2 dark:text-gray-300 dark:hover:text-white hover:bg-black/5 dark:hover:bg-white/5 rounded-xl"
								type="button"
								on:click|preventDefault={() => deleteHandler(script)}
							>
								🗑
							</button>
						</Tooltip>

						<Tooltip content={script.is_active ? $i18n.t('Enabled') : $i18n.t('Disabled')}>
							<Switch bind:state={script.is_active} on:change={() => toggleHandler(script)} />
						</Tooltip>
					</div>
				</div>
			{/each}
		</div>
	{:else}
		<div class="w-full flex flex-col justify-center items-center my-16 text-gray-400">
			<div class="text-sm">{$i18n.t('No client scripts yet.')}</div>
		</div>
	{/if}

	{#if isAdmin && globalScripts.length > 0}
		<div class="flex flex-col gap-1 mt-6 mb-1.5">
			<div class="text-lg font-medium px-0.5">{$i18n.t('Global scripts (all users)')}</div>
			<div class="text-xs text-gray-500 dark:text-gray-400 px-0.5">
				{$i18n.t('These run for every user when enabled. Authored by admins.')}
			</div>
		</div>
		<div class="my-1 gap-1 lg:gap-2 grid lg:grid-cols-2">
			{#each globalScripts as script (script.id)}
				<div
					class="flex space-x-4 w-full px-2 py-2 dark:hover:bg-white/5 hover:bg-black/5 rounded-xl border border-blue-100 dark:border-blue-900/40"
				>
					<a
						class="flex flex-1 flex-col cursor-pointer w-full"
						href={`/workspace/client-scripts/edit?id=${encodeURIComponent(script.id)}`}
					>
						<div class="font-medium line-clamp-1">{script.name}</div>
						<div class="text-xs text-gray-500 dark:text-gray-400 line-clamp-1">
							{script?.meta?.description ?? ''}
						</div>
					</a>
					<div class="flex flex-row items-center gap-2 self-center">
						<Tooltip content={$i18n.t('Remove from global')}>
							<div class="flex items-center gap-1">
								<span class="text-[10px] text-gray-400">{$i18n.t('Global')}</span>
								<Switch
									bind:state={script.is_global}
									on:change={() => toggleGlobalHandler(script)}
								/>
							</div>
						</Tooltip>
						<Tooltip content={script.is_active ? $i18n.t('Enabled') : $i18n.t('Disabled')}>
							<Switch bind:state={script.is_active} on:change={() => toggleHandler(script)} />
						</Tooltip>
					</div>
				</div>
			{/each}
		</div>
	{/if}
{/if}
