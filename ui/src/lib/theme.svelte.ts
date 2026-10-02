export type Theme = 'light' | 'dark' | 'system';

/** Also read by the inline script in app.html, which applies the theme before the first paint. */
const KEY = 'web-search-ui:theme';

class ThemeState {
	value = $state<Theme>('system');

	init() {
		try {
			const saved = localStorage.getItem(KEY);
			if (saved === 'light' || saved === 'dark') this.value = saved;
		} catch {
			// storage blocked: follow the system
		}
	}

	set(theme: Theme) {
		this.value = theme;
		const root = document.documentElement;
		if (theme === 'system') delete root.dataset.theme;
		else root.dataset.theme = theme;
		try {
			if (theme === 'system') localStorage.removeItem(KEY);
			else localStorage.setItem(KEY, theme);
		} catch {
			// not remembered, still applied
		}
	}
}

export const theme = new ThemeState();
