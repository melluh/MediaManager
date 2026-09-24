export type SubtitleFormat = { label: string; kind: 'text' | 'image' | null };

// Embedded tracks report ffprobe's codec_name, sidecars their file
// extension - both map onto the name people know the format by. Image
// formats (ripped from Blu-ray/DVD) can't be restyled or searched without
// OCR, which is worth knowing when a text track of the same language exists.
const SUBTITLE_FORMATS: Record<string, SubtitleFormat> = {
	subrip: { label: 'SRT', kind: 'text' },
	srt: { label: 'SRT', kind: 'text' },
	ass: { label: 'ASS', kind: 'text' },
	ssa: { label: 'SSA', kind: 'text' },
	webvtt: { label: 'WebVTT', kind: 'text' },
	vtt: { label: 'WebVTT', kind: 'text' },
	mov_text: { label: 'MP4 text', kind: 'text' },
	text: { label: 'Text', kind: 'text' },
	microdvd: { label: 'MicroDVD', kind: 'text' },
	hdmv_pgs_subtitle: { label: 'PGS', kind: 'image' },
	dvd_subtitle: { label: 'VobSub', kind: 'image' },
	dvb_subtitle: { label: 'DVB', kind: 'image' },
	// A .sub file is either MicroDVD text or VobSub images - can't tell
	// from the extension alone.
	sub: { label: 'SUB', kind: null }
};

export function subtitleFormat(codec: string | null | undefined): SubtitleFormat | null {
	if (!codec) return null;
	return SUBTITLE_FORMATS[codec.toLowerCase()] ?? { label: codec.toUpperCase(), kind: null };
}

export function formatAudioChannels(channels: number | null | undefined): string | null {
	if (channels == null || channels <= 0) return null;
	const named: Record<number, string> = { 1: 'mono', 2: 'stereo', 6: '5.1', 8: '7.1' };
	return named[channels] ?? `${channels} channels`;
}
