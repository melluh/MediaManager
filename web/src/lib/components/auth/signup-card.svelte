<script lang="ts">
	import { Button } from '$lib/components/ui/button';
	import * as Card from '$lib/components/ui/card';
	import { Input } from '$lib/components/ui/input';
	import { Label } from '$lib/components/ui/label';
	import { toast } from 'svelte-sonner';
	import * as Alert from '$lib/components/ui/alert';
	import AlertCircleIcon from '@lucide/svelte/icons/alert-circle';
	import LoadingBar from '$lib/components/loading-bar.svelte';
	import CheckCircle2Icon from '@lucide/svelte/icons/check-circle-2';
	import { handleOauth } from '$lib/utils.ts';
	import client from '$lib/api';
	import OAuthButtons from '$lib/components/auth/oauth-buttons.svelte';
	import { resolve } from '$app/paths';

	let email = $state('');
	let password = $state('');
	let errorMessage = $state('');
	let successMessage = $state('');
	let isLoading = $state(false);
	let confirmPassword = $state('');
	let {
		oauthProviderNames
	}: {
		oauthProviderNames: string[];
	} = $props();

	let oauthLoading = $state(false);
	async function onOauthClick() {
		oauthLoading = true;
		if (!(await handleOauth())) {
			oauthLoading = false;
		}
	}

	async function handleSignup(event: Event) {
		event.preventDefault();

		isLoading = true;
		errorMessage = '';
		successMessage = '';
		const { response } = await client.POST('/api/v1/auth/register', {
			body: {
				email: email,
				password: password,
				is_active: null,
				is_superuser: null,
				is_verified: null
			}
		});
		isLoading = false;

		if (response.ok) {
			successMessage = 'Registration successful! Please login.';
			toast.success(successMessage);
		} else {
			toast.error('Registration failed');
		}
	}
</script>

<Card.Root class="mx-auto max-w-sm">
	<Card.Header>
		<Card.Title class="text-xl">Sign Up</Card.Title>
		<Card.Description>Enter your information to create an account</Card.Description>
	</Card.Header>
	<Card.Content>
		<form class="grid gap-4" onsubmit={handleSignup}>
			<div class="grid gap-2">
				<Label for="email">Email</Label>
				<Input
					autocomplete="email"
					bind:value={email}
					id="email"
					placeholder="m@example.com"
					required
					type="email"
				/>
			</div>
			<div class="grid gap-2">
				<Label for="password">Password</Label>
				<Input
					autocomplete="new-password"
					bind:value={password}
					id="password"
					required
					type="password"
				/>
			</div>
			<div class="grid gap-2">
				<Label for="confirm-password">Confirm Password</Label>
				<Input
					autocomplete="new-password"
					bind:value={confirmPassword}
					id="confirm-password"
					required
					type="password"
				/>
			</div>
			{#if errorMessage}
				<Alert.Root variant="destructive">
					<AlertCircleIcon class="size-4" />
					<Alert.Title>Error</Alert.Title>
					<Alert.Description>{errorMessage}</Alert.Description>
				</Alert.Root>
			{/if}
			{#if successMessage}
				<Alert.Root variant="default">
					<CheckCircle2Icon class="size-4" />
					<Alert.Title>Success</Alert.Title>
					<Alert.Description>{successMessage}</Alert.Description>
				</Alert.Root>
			{/if}
			{#if isLoading}
				<LoadingBar />
			{/if}
			<Button
				class="w-full"
				disabled={isLoading || password !== confirmPassword || password === ''}
				type="submit"
				>Create an account
			</Button>
		</form>
		<OAuthButtons
			providerNames={oauthProviderNames}
			loading={oauthLoading}
			onclick={onOauthClick}
		/>
		<div class="mt-4 text-center text-sm">
			<Button href={resolve('/login/', {})} variant="link">Already have an account? Login</Button>
		</div>
	</Card.Content>
</Card.Root>
