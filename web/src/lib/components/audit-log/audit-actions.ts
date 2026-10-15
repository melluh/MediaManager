import type { Component } from 'svelte';
import type { AuditAction, AuditLogEntry } from '$lib/api/api';
import Download from '@lucide/svelte/icons/download';
import FileX from '@lucide/svelte/icons/file-x';
import FolderInput from '@lucide/svelte/icons/folder-input';
import FolderSync from '@lucide/svelte/icons/folder-sync';
import KeyRound from '@lucide/svelte/icons/key-round';
import Library from '@lucide/svelte/icons/library';
import Link from '@lucide/svelte/icons/link';
import LogIn from '@lucide/svelte/icons/log-in';
import MailCheck from '@lucide/svelte/icons/mail-check';
import Pencil from '@lucide/svelte/icons/pencil';
import Plus from '@lucide/svelte/icons/plus';
import RefreshCw from '@lucide/svelte/icons/refresh-cw';
import Repeat from '@lucide/svelte/icons/repeat';
import RotateCcw from '@lucide/svelte/icons/rotate-ccw';
import ScanSearch from '@lucide/svelte/icons/scan-search';
import ShieldAlert from '@lucide/svelte/icons/shield-alert';
import ShieldMinus from '@lucide/svelte/icons/shield-minus';
import ShieldPlus from '@lucide/svelte/icons/shield-plus';
import Trash2 from '@lucide/svelte/icons/trash-2';
import Unlink from '@lucide/svelte/icons/unlink';
import UserCheck from '@lucide/svelte/icons/user-check';
import UserPen from '@lucide/svelte/icons/user-pen';
import UserPlus from '@lucide/svelte/icons/user-plus';
import UserX from '@lucide/svelte/icons/user-x';
import X from '@lucide/svelte/icons/x';

export type AuditCategory = 'auth' | 'account' | 'user' | 'media' | 'download';

type Icon = Component<{ class?: string }>;

/** Each category reuses the icon of its most typical action. */
export const auditCategories: Record<AuditCategory, { label: string; icon: Icon }> = {
	auth: { label: 'Sign-ins', icon: LogIn },
	account: { label: 'Own account', icon: UserPen },
	user: { label: 'User management', icon: ShieldPlus },
	media: { label: 'Media', icon: Library },
	download: { label: 'Downloads', icon: Download }
};

type ActionInfo = {
	label: string;
	icon: Icon;
	/** Shown in red, for failures and things that remove data or access. */
	destructive?: boolean;
};

export const auditActions: Record<AuditAction, ActionInfo> = {
	'auth.login': { label: 'Signed in', icon: LogIn },
	'auth.login_failed': { label: 'Failed sign-in', icon: ShieldAlert, destructive: true },
	'auth.password_reset_requested': { label: 'Requested password reset', icon: KeyRound },
	'auth.password_reset': { label: 'Reset password', icon: KeyRound },
	'auth.email_verified': { label: 'Verified email', icon: MailCheck },
	'account.registered': { label: 'Signed up', icon: UserPlus },
	'account.updated': { label: 'Edited own account', icon: UserPen },
	'account.password_changed': { label: 'Changed own password', icon: KeyRound },
	'account.oauth_linked': { label: 'Linked sign-in account', icon: Link },
	'user.created': { label: 'Created user', icon: UserPlus },
	'user.updated': { label: 'Edited user', icon: UserPen },
	'user.promoted': { label: 'Made admin', icon: ShieldPlus },
	'user.demoted': { label: 'Removed admin role', icon: ShieldMinus, destructive: true },
	'user.deactivated': { label: 'Deactivated user', icon: UserX, destructive: true },
	'user.reactivated': { label: 'Reactivated user', icon: UserCheck },
	'user.approved': { label: 'Approved user', icon: UserCheck },
	'user.password_set': { label: "Set user's password", icon: KeyRound },
	'user.deleted': { label: 'Deleted user', icon: Trash2, destructive: true },
	'user.oauth_unlinked': { label: 'Unlinked sign-in account', icon: Unlink },
	'user.media_server_linked': { label: 'Linked media server account', icon: Link },
	'user.media_server_unlinked': { label: 'Unlinked media server account', icon: Unlink },
	'media.added': { label: 'Added', icon: Plus },
	'media.deleted': { label: 'Deleted', icon: Trash2, destructive: true },
	'media.file_deleted': { label: 'Deleted file', icon: FileX, destructive: true },
	'media.library_changed': { label: 'Changed library', icon: Library },
	'media.continuous_download_changed': { label: 'Changed auto-download', icon: Repeat },
	'media.metadata_refreshed': { label: 'Refreshed metadata', icon: RefreshCw },
	'media.imported': { label: 'Imported', icon: FolderInput },
	'media.files_rescanned': { label: 'Rescanned files', icon: FolderSync },
	'media.library_scanned': { label: 'Scanned library', icon: ScanSearch },
	'media.torrent_import_resolved': { label: 'Resolved import', icon: FolderInput },
	'download.started': { label: 'Started download', icon: Download },
	'download.cancelled': { label: 'Cancelled download', icon: X },
	'download.deleted': { label: 'Deleted download', icon: Trash2, destructive: true },
	'download.retried': { label: 'Retried download', icon: RotateCcw },
	'download.status_changed': { label: 'Changed download status', icon: Pencil }
};

const fieldLabels: Record<string, string> = {
	email: 'Email',
	display_name: 'Name',
	is_verified: 'Verified',
	imported: 'Imported',
	status: 'Status'
};

type Change = { from: unknown; to: unknown };

function formatValue(value: unknown): string {
	if (value === null || value === undefined || value === '') return '(none)';
	if (typeof value === 'boolean') return value ? 'yes' : 'no';
	return String(value);
}

function formatChanges(changes: unknown): string[] {
	if (!changes || typeof changes !== 'object') return [];
	return Object.entries(changes as Record<string, Change>).map(
		([field, { from, to }]) =>
			`${fieldLabels[field] ?? field}: ${formatValue(from)} → ${formatValue(to)}`
	);
}

function formatScanCounts(counts: unknown): string[] {
	if (!counts || typeof counts !== 'object') return [];
	const c = counts as Record<string, number>;
	return [
		`${c.items_scanned ?? 0} scanned`,
		c.files_adopted ? `${c.files_adopted} files adopted` : null,
		c.files_removed ? `${c.files_removed} files removed` : null,
		c.paths_relinked ? `${c.paths_relinked} paths relinked` : null
	].filter((part): part is string => part !== null);
}

/** A short, readable summary of an entry's details, one part per fact. */
export function describeEntry(entry: AuditLogEntry): string[] {
	const d = entry.details as Record<string, unknown>;
	const str = (key: string) => (typeof d[key] === 'string' ? (d[key] as string) : null);
	const parts: (string | null)[] = [];

	switch (entry.action) {
		case 'auth.login':
			parts.push(d.method === 'oidc' ? 'via single sign-on' : 'with password');
			break;
		case 'auth.login_failed':
			parts.push('wrong password');
			break;
		case 'account.registered':
			parts.push(d.method === 'oidc' ? 'via single sign-on' : null);
			break;
		case 'account.updated':
		case 'user.updated':
		case 'download.status_changed':
			parts.push(...formatChanges(d.changes));
			break;
		case 'account.oauth_linked':
		case 'user.oauth_unlinked':
			parts.push(`${str('provider')}: ${str('account_email')}`);
			break;
		case 'user.media_server_linked':
		case 'user.media_server_unlinked':
			parts.push(`${str('provider')}: ${str('username')}`);
			break;
		case 'user.created':
			parts.push(d.is_superuser ? 'as admin' : null);
			parts.push(d.password_generated ? 'generated password' : null);
			break;
		case 'user.deleted':
			parts.push(str('email'), d.was_pending ? 'rejected sign-up' : null);
			break;
		case 'media.added':
			parts.push(str('language') ? `language: ${str('language')}` : null);
			break;
		case 'media.deleted':
			parts.push(d.delete_files_on_disk ? 'with files on disk' : 'kept files on disk');
			parts.push(d.delete_torrents ? 'with downloads' : null);
			break;
		case 'media.file_deleted':
			if (typeof d.season_number === 'number') {
				const episode =
					typeof d.episode_number === 'number'
						? `E${String(d.episode_number).padStart(2, '0')}`
						: '';
				parts.push(`S${String(d.season_number).padStart(2, '0')}${episode}`);
			}
			parts.push(str('file_path_suffix') ? `version: ${str('file_path_suffix')}` : null);
			break;
		case 'media.library_changed':
			parts.push(`${str('from')} → ${str('to')}`);
			break;
		case 'media.continuous_download_changed':
			parts.push(d.enabled ? 'enabled' : 'disabled');
			break;
		case 'media.imported':
			parts.push(str('directory'));
			break;
		case 'media.library_scanned':
			parts.push(d.media_type === 'show' ? 'TV shows' : 'Movies');
			parts.push(...formatScanCounts(d.counts));
			break;
		case 'media.torrent_import_resolved':
			parts.push(str('torrent_title'), str('relative_path'));
			break;
		case 'download.started':
			parts.push(str('torrent_title'), str('indexer'), str('slot'));
			parts.push(d.usenet ? 'usenet' : null);
			break;
		case 'download.cancelled':
			parts.push(d.remove_from_client ? 'removed from download client' : null);
			break;
		case 'download.deleted':
			parts.push(d.delete_files ? 'removed from download client' : null);
			break;
	}
	return parts.filter((part): part is string => !!part);
}
