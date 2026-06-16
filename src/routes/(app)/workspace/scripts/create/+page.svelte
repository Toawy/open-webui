<script>
	import { onMount, getContext } from 'svelte';
	import { goto } from '$app/navigation';
	import { toast } from 'svelte-sonner';

	import ScriptEditor from '$lib/components/workspace/Scripts/ScriptEditor.svelte';
	import { createNewClientScript } from '$lib/apis/client-scripts';

	const i18n = getContext('i18n');

	let script = null;
	let clone = false;
	let mounted = false;

	const saveHandler = async (data) => {
		const res = await createNewClientScript(localStorage.token, {
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
			toast.success($i18n.t('Script created successfully'));
			goto('/workspace/scripts');
		}
	};

	onMount(() => {
		if (sessionStorage.script) {
			script = JSON.parse(sessionStorage.script);
			sessionStorage.removeItem('script');
			clone = true;
		}
		mounted = true;
	});
</script>

{#if mounted}
	{#key script?.content}
		<ScriptEditor
			id={script?.id ?? ''}
			name={script?.name ?? ''}
			meta={script?.meta ?? { description: '', manifest: {} }}
			content={script?.content ?? ''}
			accessGrants={script?.access_grants ?? []}
			{clone}
			onSave={(value) => saveHandler(value)}
		/>
	{/key}
{/if}
