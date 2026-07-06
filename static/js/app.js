/* global window, Vue, VueRouter, Pinia, VueUse, naive */
(function () {
    'use strict';

    if (!window.__appShared) {
        document.getElementById('app-loader').innerHTML = '<div style="color: red;">stores.js 未加载，请检查浏览器控制台</div>';
        return;
    }

    const { createApp, defineComponent, ref, computed, onMounted, h } = window.__appShared.Vue;
    const { createRouter, createWebHistory } = window.__appShared.VueRouter;
    const { createPinia } = window.__appShared.Pinia;
    const { AppLayout, useConfigStore, useThemeStore } = window.__appShared;

    // Root App component
    const App = defineComponent({
        components: { AppLayout },
        setup() {
            const themeStore = useThemeStore();
            const config = useConfigStore();
            onMounted(() => {
                config.load();
                themeStore.applyClass();
            });

            const theme = computed(() => themeStore.dark ? window.__appShared.naive.darkTheme : null);

            return { theme };
        },
        template: `
            <n-config-provider :theme="theme">
                <n-message-provider>
                    <n-dialog-provider>
                        <n-notification-provider>
                            <AppLayout>
                                <router-view />
                            </AppLayout>
                        </n-notification-provider>
                    </n-dialog-provider>
                </n-message-provider>
            </n-config-provider>
        `,
    });

    // Routes
    const routes = [
        { path: '/', name: 'series-list', component: window.SeriesList },
        { path: '/series/:series_id', name: 'series-detail', component: window.SeriesDetail },
        { path: '/daily-new', name: 'daily-new', component: window.DailyNew },
        { path: '/search', name: 'search', component: window.Search },
        { path: '/pending-cart', name: 'pending-cart', component: window.PendingCart },
        { path: '/daily-new/batches', name: 'batch-list', component: window.BatchList },
        { path: '/daily-new/batches/:batch_id', name: 'batch-detail', component: window.BatchDetail },
        { path: '/daily-new/jobs', name: 'job-list', component: window.JobList },
    ];

    const router = createRouter({
        history: createWebHistory(),
        routes,
    });

    // Create app
    const app = createApp(App);
    const pinia = createPinia();
    app.use(pinia);
    app.use(router);
    app.use(window.__appShared.naive);

    // Mount — defer 脚本执行时 readyState 是 'interactive'，DOMContentLoaded 还没触发
    // 所以只需要直接挂载即可，不要监听 DOMContentLoaded（会双重挂载）
    const loader = document.getElementById('app-loader');
    if (loader) loader.classList.add('hidden');
    app.mount('#app');
})();
