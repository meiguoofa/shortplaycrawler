/* global window, Vue */
(function () {
    'use strict';
    const { defineComponent, ref, computed, onMounted, h } = window.__appShared.Vue;
    const { apiGet, useNotify, JobStatusTag, copyText } = window.__appShared;
    const { useRouter } = window.__appShared.VueRouter;
    const { usePoll } = window.__appShared;
    const { PageShell, EmptyState, LoadingSkeleton, ErrorState } = window.__appShared;

    window.BatchList = defineComponent({
        components: { PageShell, EmptyState, LoadingSkeleton, ErrorState, JobStatusTag },
        setup() {
            const router = useRouter();
            const notify = useNotify();
            const loading = ref(true);
            const error = ref('');
            const batches = ref([]);

            async function load(opts = {}) {
                const silent = opts.silent;
                if (!silent) loading.value = true;
                error.value = '';
                try {
                    const data = await apiGet('/api/daily-new/batches');
                    batches.value = data.batches || [];
                } catch (e) {
                    if (!silent) error.value = e.message;
                    notify.error('加载失败: ' + e.message);
                } finally {
                    if (!silent) loading.value = false;
                }
            }
            onMounted(load);

            // 自动刷新（有 pending 时 10s 一次）
            const hasPending = computed(() =>
                batches.value.some(b => b.pending_count > 0)
            );
            usePoll(() => { if (hasPending.value) load({ silent: true }); }, 10000);

            // 统计
            const stats = computed(() => {
                const total = batches.value.length;
                const totalJobs = batches.value.reduce((s, b) => s + b.job_count, 0);
                const doneJobs = batches.value.reduce((s, b) => s + b.done_count, 0);
                const failedJobs = batches.value.reduce((s, b) => s + b.failed_count, 0);
                const pct = totalJobs > 0 ? Math.round(doneJobs / totalJobs * 100) : 0;
                return { total, totalJobs, doneJobs, failedJobs, pct };
            });

            function openBatch(batchId) {
                router.push('/daily-new/batches/' + batchId);
            }

            function exportBatch(batchId, format) {
                window.open('/api/daily-new/batches/' + batchId + '/export?format=' + format, '_blank');
            }

            function copyBatchId(batchId) {
                copyText(batchId).then(() => notify.success('已复制批次 ID'));
            }

            function batchStatus(b) {
                if (b.pending_count > 0) return { type: 'warning', label: '运行中' };
                if (b.failed_count > 0) return { type: 'error', label: '部分失败' };
                return { type: 'success', label: '全部完成' };
            }

            function formatMissing(nos) {
                if (!nos || !nos.length) return '';
                const limit = 5;
                const shown = nos.slice(0, limit).join('、');
                const extra = nos.length > limit ? `…等${nos.length}集` : '集';
                return `第${shown}${extra}漏选`;
            }

            return { loading, error, batches, stats, openBatch, exportBatch, copyBatchId, batchStatus, load, formatMissing };
        },
        template: `
            <page-shell title="批次列表">
                <template #actions>
                    <div class="flex flex-wrap items-center gap-4">
                        <n-statistic label="批次总数" :value="stats.total" />
                        <n-statistic label="总任务" :value="stats.totalJobs" />
                        <n-statistic label="完成" :value="stats.doneJobs" />
                        <n-statistic label="失败" :value="stats.failedJobs" />
                        <n-progress type="circle" :percentage="stats.pct" :stroke-width="6" :radius="32" />
                    </div>
                </template>

                <loading-skeleton v-if="loading" type="card-grid" />
                <error-state v-else-if="error" :message="error" @retry="load" />
                <empty-state v-else-if="batches.length === 0"
                             title="暂无批次"
                             description="请在每日上新页面勾选剧并处理。"
                             action-text="前往每日上新"
                             @action="$router.push('/daily-new')" />

                <div v-else class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                    <n-card v-for="b in batches" :key="b.batch_id"
                            hoverable class="cursor-pointer transition hover:shadow-md"
                            @click="openBatch(b.batch_id)">
                        <div class="space-y-3">
                            <div class="flex items-center justify-between">
                                <n-tooltip trigger="hover">
                                    <template #trigger>
                                        <n-text code class="text-xs cursor-pointer" @click.stop="copyBatchId(b.batch_id)">
                                            {{ b.batch_id.slice(0, 18) }}...
                                        </n-text>
                                    </template>
                                    点击复制完整 ID
                                </n-tooltip>
                                <n-tag :type="batchStatus(b).type" size="small">{{ batchStatus(b).label }}</n-tag>
                            </div>
                            <div class="text-xs text-gray-500 dark:text-gray-400">{{ b.created_at }}</div>
                            <div class="flex items-center gap-2">
                                <n-tag size="small" type="info">{{ b.target_lang }}</n-tag>
                                <span class="text-xs text-gray-500 dark:text-gray-400">{{ b.done_count }}/{{ b.job_count }} 部完成</span>
                            </div>
                            <n-progress
                                :percentage="b.job_count > 0 ? Math.round(b.done_count / b.job_count * 100) : 0"
                                :show-indicator="false"
                                :stroke-width="6"
                            />
                            <div class="text-xs text-gray-600 dark:text-gray-300">
                                剧集进度: <strong>{{ b.ep_uploaded }}</strong>/{{ b.ep_total }}
                            </div>
                            <div class="text-xs text-gray-500 dark:text-gray-400 max-h-[80px] overflow-hidden">
                                <div v-for="d in b.dramas" :key="d.id" class="truncate">
                                    • {{ d.title }}
                                    <span class="text-gray-400 dark:text-gray-500">
                                        剧集: {{ d.uploaded_eps }}/{{ d.episode_cnt || '?' }}
                                        <span v-if="d.missing_ep_nos && d.missing_ep_nos.length" class="text-orange-500 dark:text-orange-400">
                                            {{ formatMissing(d.missing_ep_nos) }}
                                        </span>
                                    </span>
                                </div>
                            </div>
                            <div class="flex gap-2 pt-3 border-t dark:border-gray-700" @click.stop>
                                <n-button size="small" type="success" :disabled="b.pending_count > 0"
                                          @click="exportBatch(b.batch_id, 'csv')">CSV</n-button>
                                <n-button size="small" type="info" :disabled="b.pending_count > 0"
                                          @click="exportBatch(b.batch_id, 'xlsx')">Excel</n-button>
                            </div>
                        </div>
                    </n-card>
                </div>
            </page-shell>
        `,
    });
})();
