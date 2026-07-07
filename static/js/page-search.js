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
            const perKeywordLimit = ref(10);
            const platformOptions = ref([]);
            const selectedPlatform = ref('hg');
            const loading = ref(false);
            const error = ref('');
            const items = ref([]);
            const selectedSeriesIds = ref([]);
            const adding = ref(false);

            onMounted(async () => {
                try {
                    const data = await apiGet('/api/search/platforms');
                    platformOptions.value = data.platforms || [];
                } catch (e) {
                    notify.error('加载平台列表失败: ' + e.message);
                }
            });

            async function search() {
                if (!keyword.value.trim()) {
                    notify.warning('请输入关键词');
                    return;
                }
                if (!selectedPlatform.value) {
                    notify.warning('请选择搜索源头');
                    return;
                }
                loading.value = true;
                error.value = '';
                submittedKeyword.value = keyword.value.trim();
                try {
                    const url = '/api/search?q=' + encodeURIComponent(submittedKeyword.value)
                              + '&limit=' + perKeywordLimit.value
                              + '&platform=' + encodeURIComponent(selectedPlatform.value);
                    const data = await apiGet(url);
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
                keyword, submittedKeyword, perKeywordLimit,
                platformOptions, selectedPlatform,
                loading, error, items,
                selectedSeriesIds, adding,
                columns, rowKey,
                search, addToCart,
            };
        },
        template: `
            <page-shell title="搜索剧集">
                <template #actions>
                    <div class="flex flex-wrap items-center gap-3">
                        <n-select v-model:value="selectedPlatform" :options="platformOptions"
                                  placeholder="选择源头" style="width: 180px;" />
                        <n-input v-model:value="keyword" placeholder="输入剧名，多个用 ; 分隔"
                                 style="width: 320px;" @keyup.enter="search" />
                        <n-input-number v-model:value="perKeywordLimit" :min="1" :max="100" :step="1"
                                        style="width: 150px;">
                            <template #prefix>每关键词</template>
                        </n-input-number>
                        <n-button type="primary" :loading="loading" @click="search">搜索</n-button>
                    </div>
                </template>

                <div v-if="submittedKeyword" class="text-sm text-gray-500 dark:text-gray-400 mb-4">
                    源头「<strong>{{ platformOptions.find(p => p.value === selectedPlatform)?.label || selectedPlatform }}</strong>」
                    关键词「<strong>{{ submittedKeyword }}</strong>」共搜到 {{ items.length }} 部剧
                    （每关键词最多 {{ perKeywordLimit }} 条，按 series_id 去重）
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
