/* global window, Vue */
(function () {
    'use strict';
    const { defineComponent, ref, onMounted, h } = window.__appShared.Vue;
    const { apiGet, useNotify, JobStatusTag } = window.__appShared;
    const { PageShell, LoadingSkeleton, ErrorState, EmptyState } = window.__appShared;

    window.SeriesDetail = defineComponent({
        components: { PageShell, LoadingSkeleton, ErrorState, EmptyState, JobStatusTag },
        setup() {
            const route = VueRouter.useRoute();
            const notify = useNotify();
            const loading = ref(true);
            const error = ref('');
            const series = ref(null);
            const episodes = ref([]);

            async function load() {
                loading.value = true;
                error.value = '';
                try {
                    const data = await apiGet('/api/series/' + route.params.series_id);
                    series.value = data.series;
                    episodes.value = data.episodes || [];
                } catch (e) {
                    error.value = e.message;
                    notify.error('加载失败: ' + e.message);
                } finally {
                    loading.value = false;
                }
            }

            onMounted(load);

            const episodeColumns = [
                { title: '#', key: 'episode_no', width: 60, align: 'center' },
                { title: '集名', key: 'episode_title', minWidth: 200 },
                { title: 'Video ID', key: 'video_id', width: 220, render: (r) => h('code', { class: 'text-xs bg-gray-100 dark:bg-gray-800 px-1.5 py-0.5 rounded' }, r.video_id) },
                {
                    title: '状态', key: 'upload_status', width: 120, align: 'center',
                    render: (r) => h(JobStatusTag, { status: r.upload_status }),
                },
                { title: '文件大小', key: 'file_size', width: 120, render: (r) => r.file_size ? (r.file_size / 1024 / 1024).toFixed(1) + ' MB' : '-' },
                {
                    title: 'TOS URL', key: 'object_storage_url', minWidth: 120,
                    render: (r) => r.object_storage_url ? h('a', {
                        href: r.object_storage_url,
                        target: '_blank',
                        class: 'text-primary hover:underline text-sm',
                    }, '查看 →') : '-',
                },
            ];

            return { loading, error, series, episodes, episodeColumns, load };
        },
        template: `
            <page-shell title="剧集详情" show-back back-path="/">
                <loading-skeleton v-if="loading" type="hero" />
                <error-state v-else-if="error" :message="error" @retry="load" />
                <template v-else-if="series">
                    <n-card>
                        <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
                            <div class="flex justify-center md:justify-start">
                                <img v-if="series.cover_url" :src="series.cover_url" :alt="series.title"
                                     class="w-full max-w-[280px] rounded-lg shadow-md object-cover" />
                                <div v-else class="w-full max-w-[280px] aspect-[2/3] bg-gray-100 dark:bg-gray-700 rounded-lg flex items-center justify-center text-gray-400">
                                    无海报
                                </div>
                            </div>
                            <div class="md:col-span-2 space-y-4">
                                <h2 class="text-xl md:text-2xl font-semibold">{{ series.title }}</h2>
                                <n-descriptions :column="2" label-placement="left" size="medium">
                                    <n-descriptions-item label="类型">{{ series.genre_type || '-' }}</n-descriptions-item>
                                    <n-descriptions-item label="分类">{{ series.category || '-' }}</n-descriptions-item>
                                    <n-descriptions-item label="作者">{{ series.author || '-' }}</n-descriptions-item>
                                    <n-descriptions-item label="版权">{{ series.copyright || '-' }}</n-descriptions-item>
                                    <n-descriptions-item label="时长">{{ series.duration || '-' }}</n-descriptions-item>
                                    <n-descriptions-item label="总集数">{{ series.total_episodes || series.episode_cnt || '-' }}</n-descriptions-item>
                                    <n-descriptions-item label="播放数">{{ series.play_cnt ? Number(series.play_cnt).toLocaleString() : '-' }}</n-descriptions-item>
                                    <n-descriptions-item label="评分">{{ series.score || '-' }}</n-descriptions-item>
                                </n-descriptions>
                                <div v-if="series.detail_desc">
                                    <div class="text-sm text-gray-500 dark:text-gray-400 mb-1">简介</div>
                                    <p class="text-sm text-gray-700 dark:text-gray-300 leading-relaxed">{{ series.detail_desc }}</p>
                                </div>
                            </div>
                        </div>
                    </n-card>

                    <n-card title="剧集列表">
                        <empty-state v-if="episodes.length === 0" title="暂无剧集数据" />
                        <n-data-table v-else
                            :columns="episodeColumns"
                            :data="episodes"
                            :pagination="{ pageSize: 50 }"
                            :scroll-x="900"
                            size="medium"
                            striped
                        />
                    </n-card>
                </template>
            </page-shell>
        `,
    });
})();
