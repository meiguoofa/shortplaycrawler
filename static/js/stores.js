/* global Vue, VueRouter, Pinia, VueUse, naive */

(function () {
    'use strict';

    const { createApp, ref, reactive, computed, onMounted, watch, defineComponent, h } = Vue;
    const { createRouter, createWebHistory } = VueRouter;
    const { defineStore } = Pinia;

    // setInterval-based polling helper (替代 useIntervalFn — VueUse 12 已移除)
    // 在 setup 中调用：返回 { start, stop }；调用方需在 onMounted 中 start()
    function usePoll(fn, intervalMs) {
        let timer = null;
        const start = () => { if (timer === null) timer = setInterval(fn, intervalMs); };
        const stop = () => { if (timer !== null) { clearInterval(timer); timer = null; } };
        // 自动在 onMounted 时启动
        Vue.onMounted(start);
        Vue.onUnmounted(stop);
        return { start, stop, resume: start, pause: stop };
    }

    // ─────────────────────────────────────────────────────────────────────
    // Stores
    // ─────────────────────────────────────────────────────────────────────

    const useConfigStore = defineStore('config', {
        state: () => ({
            langs: {},
            imageModels: [],
            defaultImageModel: '',
            defaultImagePrompt: '',
            defaultTranslateSystemPrompt: '',
            defaultTranslateUserPrompt: '',
            loaded: false,
        }),
        actions: {
            async load() {
                if (this.loaded) return;
                try {
                    const r = await fetch('/api/config/defaults');
                    const data = await r.json();
                    Object.assign(this, data);
                    this.loaded = true;
                } catch (e) {
                    console.error('Failed to load config:', e);
                }
            },
        },
    });

    const useThemeStore = defineStore('theme', {
        state: () => ({
            dark: localStorage.getItem('theme') === 'dark',
        }),
        actions: {
            applyClass() {
                const html = document.documentElement;
                if (this.dark) html.classList.add('dark');
                else html.classList.remove('dark');
            },
            toggle() {
                this.dark = !this.dark;
                localStorage.setItem('theme', this.dark ? 'dark' : 'light');
                this.applyClass();
            },
        },
    });

    // Naive UI message helpers (must be called inside setup)
    const useNotify = () => {
        const message = naive.useMessage();
        return {
            success: (msg) => message.success(msg, { duration: 4000 }),
            error: (msg) => message.error(msg, { duration: 4000 }),
            warning: (msg) => message.warning(msg, { duration: 4000 }),
            info: (msg) => message.info(msg, { duration: 4000 }),
        };
    };

    // ─────────────────────────────────────────────────────────────────────
    // API helpers
    // ─────────────────────────────────────────────────────────────────────

    async function apiGet(url) {
        const r = await fetch(url);
        if (!r.ok) {
            const err = await r.json().catch(() => ({ error: r.statusText }));
            throw new Error(err.error || `HTTP ${r.status}`);
        }
        return r.json();
    }

    async function apiPost(url, body) {
        const r = await fetch(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body),
        });
        if (!r.ok) {
            const err = await r.json().catch(() => ({ error: r.statusText }));
            throw new Error(err.error || `HTTP ${r.status}`);
        }
        return r.json();
    }

    function genBatchId() {
        if (crypto && crypto.randomUUID) return crypto.randomUUID();
        return 'batch_' + Date.now();
    }

    function substitute(template, vars) {
        let result = template || '';
        for (const [key, value] of Object.entries(vars)) {
            result = result.split('{' + key + '}').join(value);
        }
        return result;
    }

    function truncate(s, n) {
        if (!s) return '';
        return s.length > n ? s.slice(0, n) + '...' : s;
    }

    function formatDateTime(iso) {
        if (!iso) return '-';
        const d = new Date(iso);
        if (isNaN(d)) return iso;
        const pad = (n) => String(n).padStart(2, '0');
        return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`;
    }

    function statusBadgeType(status) {
        return {
            done: 'success',
            failed: 'error',
            pending: 'warning',
            translating: 'info',
            poster_generating: 'info',
            processing_episodes: 'info',
        }[status] || 'default';
    }

    function statusLabel(status) {
        return {
            done: '✅ 完成',
            failed: '❌ 失败',
            pending: '⏳ 待处理',
            translating: '🔄 翻译中',
            poster_generating: '🎨 生成海报',
            processing_episodes: '📦 处理剧集',
        }[status] || status;
    }

    // ─────────────────────────────────────────────────────────────────────
    // App layout (nav + content)
    // ─────────────────────────────────────────────────────────────────────

    const AppLayout = defineComponent({
        setup() {
            const themeStore = useThemeStore();
            const router = VueRouter.useRouter();
            const route = VueRouter.useRoute();
            const mobileMenuOpen = ref(false);

            const menuOptions = computed(() => [
                { label: '剧集列表', key: 'series', path: '/' },
                { label: '每日上新', key: 'daily-new', path: '/daily-new' },
                { label: '批次列表', key: 'batches', path: '/daily-new/batches' },
                { label: '翻译任务', key: 'jobs', path: '/daily-new/jobs' },
            ]);

            const activeKey = computed(() => {
                if (route.path === '/') return 'series';
                if (route.path === '/daily-new') return 'daily-new';
                if (route.path === '/daily-new/batches') return 'batches';
                if (route.path === '/daily-new/jobs') return 'jobs';
                return '';
            });

            function onMenu(key) {
                const item = menuOptions.value.find(m => m.key === key);
                if (item) {
                    router.push(item.path);
                    mobileMenuOpen.value = false;
                }
            }

            function toggleTheme() {
                themeStore.toggle();
            }

            return { themeStore, menuOptions, activeKey, onMenu, toggleTheme, mobileMenuOpen };
        },
        template: `
            <n-layout position="absolute">
                <n-layout-header bordered class="px-4 md:px-6 py-3 flex items-center justify-between">
                    <div class="flex items-center gap-4 md:gap-6">
                        <span class="text-lg font-semibold">短剧数据管理</span>
                        <div class="hidden md:block">
                            <n-menu mode="horizontal" :options="menuOptions" :value="activeKey"
                                    @select="onMenu" />
                        </div>
                    </div>
                    <div class="flex items-center gap-2">
                        <n-button id="theme-toggle" quaternary circle @click="toggleTheme">
                            <template #icon>
                                <span>{{ themeStore.dark ? '🌙' : '☀️' }}</span>
                            </template>
                        </n-button>
                        <n-button class="md:hidden" quaternary circle @click="mobileMenuOpen = true">
                            <template #icon>
                                <span>☰</span>
                            </template>
                        </n-button>
                    </div>
                </n-layout-header>

                <n-drawer v-model:show="mobileMenuOpen" placement="left" width="220">
                    <n-menu :options="menuOptions" :value="activeKey" @select="onMenu" />
                </n-drawer>

                <n-layout-content class="p-4 md:p-6 lg:p-8">
                    <div class="max-w-7xl mx-auto">
                        <slot />
                    </div>
                </n-layout-content>
            </n-layout>
        `,
    });

    // 暴露给子组件
    window.__appShared = {
        Vue, VueRouter, Pinia, VueUse, naive,
        defineComponent, ref, reactive, computed, onMounted, watch, h,
        useConfigStore, useThemeStore,
        apiGet, apiPost, genBatchId, substitute, truncate,
        formatDateTime, statusBadgeType, statusLabel, AppLayout,
        usePoll, useNotify,
    };
})();
