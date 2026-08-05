<script lang="ts">
	import { Button } from '$lib/components/ui/button';
	import * as Card from '$lib/components/ui/card';
	import { Input } from '$lib/components/ui/input';
	import { Label } from '$lib/components/ui/label';
	import { goto } from '$app/navigation';
	import * as Alert from '$lib/components/ui/alert';
	import AlertCircleIcon from '@lucide/svelte/icons/alert-circle';
	import LogInIcon from '@lucide/svelte/icons/log-in';
	import UserPlusIcon from '@lucide/svelte/icons/user-plus';
	import client from '$lib/api';
	import { handleOauth } from '$lib/utils.ts';
	import { resolve } from '$app/paths';
	import { CheckIcon } from 'lucide-svelte';
	import Spinner from '../ui/spinner/spinner.svelte';

	let {
		oauthProviderNames,
		registrationEnabled,
		passwordLoginEnabled
	}: {
		oauthProviderNames: string[];
		registrationEnabled: boolean;
		passwordLoginEnabled: boolean;
	} = $props();

	let email = $state('');
	let password = $state('');
	let status = $state<'idle' | 'loading' | 'success' | 'error'>('idle');

	let singleOauthOnly = $derived(!passwordLoginEnabled && oauthProviderNames.length === 1);

	async function handleLogin(event: Event) {
		event.preventDefault();

		status = 'loading';

		const { error, response } = await client.POST('/api/v1/auth/cookie/login', {
			body: {
				username: email,
				password: password,
				scope: ''
			},
			headers: {
				'Content-Type': 'application/x-www-form-urlencoded'
			}
		});

		if (!error) {
			console.log('Login successful!');
			console.log('Received User Data: ', response);
			status = 'success';
			await goto(resolve('/dashboard', {}));
		} else {
			status = 'error';
		}
	}
</script>

<Card.Root class="mx-auto max-w-sm">
	<Card.Header>
		<Card.Title class="text-2xl">Login</Card.Title>
		{#if passwordLoginEnabled}
			<Card.Description>Enter your details below to log in to your account.</Card.Description>
		{:else if oauthProviderNames.length == 1}
			<Card.Description
				>Continue with {oauthProviderNames[0]} to access your account.</Card.Description
			>
		{/if}
	</Card.Header>
	<Card.Content>
		{#if !passwordLoginEnabled && oauthProviderNames.length === 0}
			<Alert.Root variant="destructive">
				<AlertCircleIcon class="size-4" />
				<Alert.Title>No login methods available</Alert.Title>
				<Alert.Description>
					There are currently no login methods configured. Please contact your administrator.
				</Alert.Description>
			</Alert.Root>
		{:else}
			{#if passwordLoginEnabled}
				<form class="grid gap-4" onsubmit={handleLogin}>
					{#if status === 'error'}
						<Alert.Root variant="destructive">
							<AlertCircleIcon class="size-4" />
							<Alert.Title>Login failed</Alert.Title>
							<Alert.Description>Please check your credentials and try again.</Alert.Description>
						</Alert.Root>
					{/if}

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
						<div class="flex items-center">
							<Label for="password">Password</Label>
							<a
								class="ml-auto inline-block text-sm underline"
								href={resolve('/login/forgot-password', {})}
							>
								Forgot your password?
							</a>
						</div>
						<Input
							autocomplete="current-password"
							bind:value={password}
							id="password"
							required
							type="password"
						/>
					</div>

					<Button
						class="w-full"
						disabled={status === 'loading' || status === 'success'}
						type="submit"
					>
						{#if status === 'success'}
							<CheckIcon />
						{:else if status === 'loading'}
							<Spinner />
						{:else}
							<LogInIcon class="size-4" />
						{/if}
						Login
					</Button>
				</form>
			{/if}

			{#if passwordLoginEnabled}
				<div
					class="relative mt-4 text-center text-sm after:absolute after:inset-0 after:top-1/2 after:z-0 after:flex after:items-center after:border-t after:border-border"
				>
					<span class="relative z-10 bg-background px-2 text-muted-foreground">
						Or continue with
					</span>
				</div>
			{/if}

			{#each oauthProviderNames as name, i (name)}
				<Button
					class={passwordLoginEnabled || i > 0 ? 'mt-2 w-full' : 'w-full'}
					onclick={() => handleOauth()}
					variant={singleOauthOnly ? 'default' : 'outline'}
				>
					{#if singleOauthOnly}<LogInIcon class="size-4" />{/if}
					Login with {name}
				</Button>
			{/each}

			{#if registrationEnabled}
				<div class="mt-6 text-center text-sm">
					<Button href={resolve('/login/signup/', {})} variant="link">
						<UserPlusIcon class="size-4" />
						Don't have an account? Sign up
					</Button>
				</div>
			{/if}
		{/if}
	</Card.Content>
</Card.Root>
