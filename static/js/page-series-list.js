/* global window, Vue */
(function () {
    'use strict';
    const { defineComponent, ref, reactive, computed, onMounted, h } = window.__appShared.Vue;
    const { apiGet, useNotify } = window.__appShared;
    const { PageShell, EmptyState, LoadingSkeleton, ErrorState } = window.__appShared;

    window.SeriesList = defineComponent({
        components: { PageShell, EmptyState, LoadingSkeleton, ErrorState },
        setup() {
            const notify = useNotify();
            const loading = ref(true);
            const error = ref('');
            const series = ref([]);
            const filters = reactive({
                genre_type: '',
                category: '',
                sort: 'rank_order',
                order: 'asc',
            });

            const genreOptions = [
                { label: '全部类型', value: '' },
                { label: '漫剧', value: '漫剧' },
                { label: 'AI短剧', value: 'AI短剧' },
            ];
            const categoryOptions = [
                { label: '全部分类', value: '' },
                { label: '奇幻', value: '奇幻' },
                { label: '玄幻', value: '玄幻' },
                { label: '豪门', value: '豪门' },
            ];
            const sortOptions = [
                { label: '爬取顺序', value: 'rank_order' },
                { label: '播放数', value: 'play_cnt' },
                { label: '热度', value: 'hot_content_value' },
                { label: 'Hot Score', value: 'hot_score' },
            ];
            const orderOptions = [
                { label: '升序', value: 'asc' },
                { label: '降序', value: 'desc' },
            ];

            async function load() {
                loading.value = true;
                error.value = '';
                try {
                    const params = new URLSearchParams();
                    Object.entries(filters).forEach(([k, v]) => { if (v) params.set(k, v); });
                    const data = await apiGet('/api/series?' + params.toString());
                    series.value = data.series || [];
                } catch (e) {
                    error.value = e.message;
                    notify.error('加载失败: ' + e.message);
                } finally {
                    loading.value = false;
                }
            }

            onMounted(load);

            const columns = computed(() => [
                { title: '排名', key: 'rank_order', width: 70, align: 'center' },
                {
                    title: '海报', key: 'cover_url', width: 90, align: 'center',
                    render(row) {
                        return row.cover_url ? h('img', {
                            src: row.cover_url,
                            alt: row.title,
                            class: 'w-[50px] h-[70px] object-cover rounded shadow mx-auto',
                            loading: 'lazy',
                        }) : h('div', { class: 'w-[50px] h-[70px] bg-gray-100 dark:bg-gray-700 rounded mx-auto flex items-center justify-center text-xs text-gray-400' }, '无');
                    },
                },
                {
                    title: '标题', key: 'title', minWidth: 200,
                    render(row) {
                        return h('a', {
                            href: '/series/' + row.series_id,
                            onClick: (e) => { e.preventDefault(); window.__appShared.VueRouter.useRouter?.().push('/series/' + row.series_id); },
                            class: 'text-primary hover:underline font-medium',
                        }, row.title);
                    },
                },
                { title: '类型', key: 'genre_type', width: 100 },
                { title: '分类', key: 'category', width: 100 },
                {
                    title: '播放数', key: 'play_cnt', width: 120,
                    render(row) { return row.play_cnt != null ? Number(row.play_cnt).toLocaleString() : '-'; },
                },
                { title: '热度', key: 'hot_content', width: 120 },
                { title: '集数', key: 'episode_cnt', width: 80, align: 'center' },
                { title: '作者', key: 'author', width: 140 },
                {
                    title: '视频进度', key: 'ep', width: 120, align: 'center',
                    render(row) {
                        return h('span', { class: 'text-xs' }, `${row.episodes_uploaded || 0}/${row.episodes_total || 0}`);
                    },
                },
            ]);

            function applyFilters() { load(); }
            function resetFilters() {
                filters.genre_type = '';
                filters.category = '';
                filters.sort = 'rank_order';
                filters.order = 'asc';
                load();
            }

            return {
                loading, error, series, filters,
                genreOptions, categoryOptions, sortOptions, orderOptions,
                columns, applyFilters, resetFilters, load,
            };
        },
        template: `
            <page-shell title="剧集列表" :subtitle="'共 ' + series.length + ' 部剧集'">
                <n-card class="mb-6">
                    <div class="flex flex-wrap gap-4 items-end">
                        <div class="min-w-[140px]">
                            <div class="text-sm text-gray-500 dark:text-gray-400 mb-1">类型</div>
                            <n-select v-model:value="filters.genre_type" :options="genreOptions" />
                        </div>
                        <div class="min-w-[140px]">
                            <div class="text-sm text-gray-500 dark:text-gray-400 mb-1">分类</div>
                            <n-select v-model:value="filters.category" :options="categoryOptions" />
                        </div>
                        <div class="min-w-[140px]">
                            <div class="text-sm text-gray-500 dark:text-gray-400 mb-1">排序</div>
                            <n-select v-model:value="filters.sort" :options="sortOptions" />
                        </div>
                        <div class="min-w-[100px]">
                            <div class="text-sm text-gray-500 dark:text-gray-400 mb-1">顺序</div>
                            <n-select v-model:value="filters.order" :options="orderOptions" />
                        </div>
                        <n-button type="primary" @click="applyFilters">应用</n-button>
                        <n-button @click="resetFilters">重置</n-button>
                    </div>
                </n-card>

                <loading-skeleton v-if="loading" type="list" :rows="6" />
                <error-state v-else-if="error" :message="error" @retry="load" />
                <div v-else-if="series.length === 0">
                    <empty-state title="暂无剧集"
                                 description="当前筛选条件下没有数据，尝试重置筛选条件。"
                                 action-text="重置筛选"
                                 @action="resetFilters" />
                </div>
                <n-card v-else title="榜单剧集">
                    <n-data-table
                        :columns="columns"
                        :data="series"
                        :pagination="{ pageSize: 20 }"
                        :scroll-x="1000"
                        size="medium"
                        striped
                    />
                </n-card>
            </page-shell>
        `,
    });
})();
