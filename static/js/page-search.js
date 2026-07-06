/* global window, Vue */
(function () {
    'use strict';
    const { defineComponent, ref, reactive, computed, onMounted, h } = window.__appShared.Vue;
    const { apiGet, apiPost, useNotify } = window.__appShared;
    const { useRouter } = window.__appShared.VueRouter;
    const { PageShell, EmptyState, LoadingSkeleton, ErrorState } = window.__appShared;

    window.Search = defineComponent({
        components: { PageShell, EmptyState, LoadingSkeleton, ErrorState },
        setup() {
            const router = useRouter();
            const notify = useNotify();

            const keyword = ref('');
            const submittedKeyword = ref('');
            const loading = ref(false);
            const error = ref('');
            const items = ref([]);
            const selectedSeriesIds = ref([]);
            const adding = ref(false);

            async function search() {
                if (!keyword.value.trim()) {
                    notify.warning('请输入关键词');
                    return;
                }
                loading.value = true;
                error.value = '';
                submittedKeyword.value = keyword.value.trim();
                try {
                    const data = await apiGet('/api/search?q=' + encodeURIComponent(submittedKeyword.value));
                    items.value = data.items || [];
                    selectedSeriesIds.value = [];
                    if (items.value.length === 0) notify.info('未搜到任何剧');
                } catch (e) {
                    error.value = e.message;
                    notify.error('搜索失败: ' + e.message);
                } finally {
                    loading.value = false;
                }
            }

            async function addToCart() {
                if (selectedSeriesIds.value.length === 0) {
                    notify.warning('请至少勾选一部剧');
                    return;
                }
                adding.value = true;
                try {
                    const selected = items.value.filter(it => selectedSeriesIds.value.includes(it.series_id));
                    const data = await apiPost('/api/pending-cart', { items: selected });
                    notify.success(`已加入清单 ${data.added} 部（重复 ${selected.length - data.added} 部已跳过）`);
                    selectedSeriesIds.value = [];
                } catch (e) {
                    notify.error('加入失败: ' + e.message);
                } finally {
                    adding.value = false;
                }
            }

            const columns = computed(() => [
                { type: 'selection' },
                {
                    title: '海报', key: 'cover_url', width: 90, align: 'center',
                    render: (row) => row.cover_url ? h('img', {
                        src: row.cover_url,
                        alt: row.title,
                        class: 'w-[50px] h-[70px] object-cover rounded shadow mx-auto',
                        loading: 'lazy',
                    }) : h('div', { class: 'w-[50px] h-[70px] bg-gray-100 dark:bg-gray-700 rounded mx-auto flex items-center justify-center text-xs text-gray-400' }, '无'),
                },
                {
                    title: '剧名', key: 'title', minWidth: 200,
                    render: (row) => h('div', [
                        h('div', { class: 'font-medium' }, row.title),
                        h('div', { class: 'text-xs text-gray-500 dark:text-gray-400 mt-0.5' },
                          `${row.author || '未知作者'} · ${row.category || '-'} · ${row.episode_cnt || '?'} 集`),
                    ]),
                },
                { title: '分类', key: 'category', width: 120 },
                { title: '集数', key: 'episode_cnt', width: 80, align: 'center' },
                {
                    title: '简介', key: 'description', minWidth: 280,
                    render: (row) => h('div', {
                        class: 'max-w-[360px] truncate text-sm text-gray-600 dark:text-gray-300',
                        title: row.description || '',
                    }, row.description || '-'),
                },
            ]);

            const rowKey = (row) => row.series_id;

            return {
                keyword, submittedKeyword, loading, error, items,
                selectedSeriesIds, adding,
                columns, rowKey,
                search, addToCart,
            };
        },
        template: `
            <page-shell title="搜索剧集">
                <template #actions>
                    <div class="flex flex-wrap items-center gap-3">
                        <n-input v-model:value="keyword" placeholder="输入剧名关键词"
                                 style="width: 240px;" @keyup.enter="search" />
                        <n-button type="primary" :loading="loading" @click="search">搜索</n-button>
                    </div>
                </template>

                <div v-if="submittedKeyword" class="text-sm text-gray-500 dark:text-gray-400 mb-4">
                    关键词「<strong>{{ submittedKeyword }}</strong>」共搜到 {{ items.length }} 部剧（来自 5 个平台聚合，已按 series_id 去重）
                </div>

                <loading-skeleton v-if="loading" type="list" :rows="6" />
                <error-state v-else-if="error" :message="error" @retry="search" />
                <template v-else>
                    <n-card v-if="items.length > 0" title="搜索结果">
                        <n-data-table
                            :columns="columns"
                            :data="items"
                            :row-key="rowKey"
                            v-model:checked-row-keys="selectedSeriesIds"
                            :pagination="{ pageSize: 20 }"
                            :scroll-x="1100"
                            size="medium"
                            striped
                        />
                    </n-card>
                    <empty-state v-else-if="submittedKeyword" title="未搜到任何剧" />
                </template>

                <!-- 底部 sticky 操作栏 -->
                <div v-if="selectedSeriesIds.length > 0" class="sticky bottom-0 left-0 right-0 bg-white/90 dark:bg-gray-800/90 backdrop-blur border-t dark:border-gray-700 shadow-lg p-4 -mx-4 md:-mx-6 lg:-mx-8">
                    <div class="max-w-7xl mx-auto flex items-center justify-between gap-3">
                        <div class="text-sm text-gray-600 dark:text-gray-300">
                            已选 <strong>{{ selectedSeriesIds.length }}</strong> 部剧
                        </div>
                        <n-button type="primary" size="large" :loading="adding" @click="addToCart">
                            加入待处理清单
                        </n-button>
                    </div>
                </div>
            </page-shell>
        `,
    });
})();
