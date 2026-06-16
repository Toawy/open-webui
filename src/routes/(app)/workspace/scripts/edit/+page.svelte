<script>
	import { onMount, getContext } from 'svelte';
	import { goto } from '$app/navigation';
	import { page } from '$app/stores';
	import { toast } from 'svelte-sonner';

	import ScriptEditor from '$lib/components/workspace/Scripts/ScriptEditor.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import { getClientScriptById, updateClientScriptById } from '$lib/apis/client-scripts';

	const i18n = getContext('i18n');

	let script = null;

	const saveHandler = async (data) => {
		const res = await updateClientScriptById(localStorage.token, script.id, {
			id: data.id,
			name: data.name,
			meta: data.meta,
			content: data.content,
			access_grants: data.access_grants
		}).catch((e) => {
			toast.error(`${e}`);
			return null;
		});

		if (res) {
			toast.success($i18n.t('Script updated successfully'));
			goto('/workspace/scripts');
		}
	};

	onMount(async () => {
		const id = $page.url.searchParams.get('id');
		if (id) {
			const res = await getClientScriptById(localStorage.token, id).catch((e) => {
				toast.error(`${e}`);
				return null;
			});

			if (res && res.write_access === false) {
				toast.error($i18n.t('You do not have permission to edit this script'));
				goto('/workspace/scripts');
				return;
			}
			if (res) {
				script = res;
			}
		}
	});
</script>

{#if script}
	<ScriptEditor
		edit={true}
		id={script.id}
		name={script.name}
		meta={script.meta}
		content={script.content}
		accessGrants={script.access_grants ?? []}
		onSave={(value) => saveHandler(value)}
	/>
{:else}
	<Spinner className="size-5" />
{/if}
