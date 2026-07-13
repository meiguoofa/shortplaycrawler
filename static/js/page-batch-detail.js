/* global window, Vue */
(function () {
    'use strict';
    const { defineComponent, ref, computed, onMounted, h } = window.__appShared.Vue;
    const { apiGet, apiPost, useNotify, useDialog, JobStatusTag } = window.__appShared;
    const { useRoute, useRouter } = window.__appShared.VueRouter;
    const { usePoll } = window.__appShared;
    const { PageShell, LoadingSkeleton, ErrorState, Breadcrumbs } = window.__appShared;

    window.BatchDetail = defineComponent({
        components: { PageShell, LoadingSkeleton, ErrorState, Breadcrumbs, JobStatusTag },
        setup() {
            const route = useRoute();
            const router = useRouter();
            const notify = useNotify();
            const dialog = useDialog();
            const loading = ref(true);
            const error = ref('');
            const batch = ref(null);
            const activeNames = ref([]);
            const retrying = ref(false);
            const retryingJobId = ref(null);

            async function load(opts = {}) {
                const silent = opts.silent;
                if (!silent) loading.value = true;
                error.value = '';
                try {
                    const data = await apiGet('/api/daily-new/batches/' + route.params.batch_id);
                    batch.value = data;
                    if (activeNames.value.length === 0 && data.jobs) {
                        activeNames.value = data.jobs.slice(0, 3).map(j => String(j.id));
                    }
                } catch (e) {
                    if (!silent) error.value = e.message;
                    notify.error('加载失败: ' + e.message);
                } finally {
                    if (!silent) loading.value = false;
                }
            }
            onMounted(load);

            const hasPending = computed(() =>
                batch.value && batch.value.jobs &&
                batch.value.jobs.some(j => !['done', 'failed'].includes(j.status))
            );
            usePoll(() => { if (hasPending.value) load({ silent: true }); }, 10000);

            const breadcrumbs = computed(() => [
                { label: '批次列表', path: '/daily-new/batches' },
                { label: batch.value ? batch.value.batch_id.slice(0, 12) + '...' : '详情' },
            ]);

            function formatMissing(nos) {
                if (!nos || !nos.length) return '';
                const limit = 5;
                const shown = nos.slice(0, limit).join('、');
                const extra = nos.length > limit ? `…等${nos.length}集` : '集';
                return `第${shown}${extra}漏选`;
            }

            function retryAllFailed() {
                dialog.confirm({
                    title: '重试所有失败',
                    content: '将重新生成失败海报并补抓所有漏选剧集。已上传的剧集不会重复处理。',
                    positiveText: '开始重试',
                    onConfirm: async () => {
                        retrying.value = true;
                        try {
                            const data = await apiPost(
                                '/api/daily-new/batches/' + route.params.batch_id + '/retry',
                                { retry_posters: true, retry_episodes: true }
                            );
                            notify.success(`已提交重试: ${data.retried_count} 部剧`);
                            await load({ silent: false });
                        } catch (e) {
                            notify.error('重试失败: ' + e.message);
                        } finally {
                            retrying.value = false;
                        }
                    },
                });
            }

            function retryJob(job, mode) {
                // mode: 'poster' | 'episodes' | 'all'
                const body = mode === 'poster'
                    ? { drama_ids: [job.daily_new_drama_id], retry_posters: true, retry_episodes: false }
                    : mode === 'episodes'
                    ? { drama_ids: [job.daily_new_drama_id], retry_posters: false, retry_episodes: true }
                    : { drama_ids: [job.daily_new_drama_id], retry_posters: true, retry_episodes: true };
                const label = mode === 'poster' ? '海报' : mode === 'episodes' ? '漏集' : '全部';
                dialog.confirm({
                    title: `重试${label}`,
                    content: `剧名: ${job.drama ? job.drama.title : '?'}${mode === 'episodes' ? '（仅补抓漏选剧集，不重新生成海报）' : ''}`,
                    positiveText: '确认重试',
                    onConfirm: async () => {
                        retryingJobId.value = job.id;
                        try {
                            await apiPost(
                                '/api/daily-new/batches/' + route.params.batch_id + '/retry',
                                body
                            );
                            notify.success(`已提交重试: ${label}`);
                            await load({ silent: false });
                        } catch (e) {
                            notify.error('重试失败: ' + e.message);
                        } finally {
                            retryingJobId.value = null;
                        }
                    },
                });
            }

            return { loading, error, batch, activeNames, breadcrumbs, load, formatMissing, retrying, retryingJobId, retryAllFailed, retryJob };
        },
        template: `
            <page-shell v-if="batch" :title="batch.batch_id.slice(0, 16) + '...'" subtitle="批次详情">
                <breadcrumbs :items="breadcrumbs" />

                <loading-skeleton v-if="loading" type="list" :rows="6" />
                <error-state v-else-if="error" :message="error" @retry="load" />
                <template v-else-if="batch">
                    <n-card class="mb-6">
                        <div class="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
                            <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
                                <n-statistic label="总任务" :value="batch.total_jobs" />
                                <n-statistic label="完成" :value="batch.done_count">
                                    <template #suffix>
                                        <span class="text-emerald-600">✓</span>
                                    </template>
                                </n-statistic>
                                <n-statistic label="失败" :value="batch.failed_count">
                                    <template #suffix>
                                        <span class="text-red-600">✗</span>
                                    </template>
                                </n-statistic>
                                <n-statistic label="运行中" :value="batch.pending_count">
                                    <template #suffix>
                                        <span class="text-amber-600">⟳</span>
                                    </template>
                                </n-statistic>
                            </div>
                            <div class="flex gap-2">
                                <n-button size="small" type="warning" :loading="retrying"
                                          :disabled="batch.pending_count > 0 || (batch.failed_count === 0 && !batch.jobs.some(j => j.missing_ep_nos && j.missing_ep_nos.length))"
                                          @click="retryAllFailed">重试所有失败</n-button>
                                <n-button size="small" type="success" :disabled="batch.pending_count > 0"
                                          @click="$router.push('/api/daily-new/batches/' + batch.batch_id + '/export?format=csv')">导出 CSV</n-button>
                                <n-button size="small" type="info" :disabled="batch.pending_count > 0"
                                          @click="$router.push('/api/daily-new/batches/' + batch.batch_id + '/export?format=xlsx')">导出 Excel</n-button>
                            </div>
                        </div>
                    </n-card>

                    <n-card title="任务明细">
                        <n-collapse v-model:expanded-names="activeNames" accordion>
                            <n-collapse-item v-for="job in batch.jobs" :key="job.id" :name="String(job.id)">
                                <template #header>
                                    <div class="flex flex-wrap items-center gap-3 w-full">
                                        <job-status-tag :status="job.status" size="small" />
                                        <span class="font-medium">{{ job.drama ? job.drama.title : '?' }}</span>
                                        <n-tag size="small" type="info">{{ job.target_lang }}</n-tag>
                                        <span class="text-xs text-gray-500 dark:text-gray-400">
                                            剧集: {{ job.uploaded_episodes }}/{{ job.total_episodes }}
                                        </span>
                                        <span v-if="job.missing_ep_nos && job.missing_ep_nos.length"
                                              class="text-xs text-orange-500 dark:text-orange-400">
                                            {{ formatMissing(job.missing_ep_nos) }}
                                        </span>
                                        <span v-if="job.error_message" class="text-xs text-red-500 truncate max-w-[200px]">
                                            ⚠️ {{ job.error_message.slice(0, 50) }}
                                        </span>
                                    </div>
                                </template>
                                <template #header-extra>
                                    <div class="flex items-center gap-2">
                                        <n-button v-if="job.error_message && job.error_message.startsWith('poster_gen:')"
                                                  size="tiny" type="warning" :loading="retryingJobId === job.id"
                                                  @click.stop="retryJob(job, 'poster')">重试海报</n-button>
                                        <n-button v-if="job.missing_ep_nos && job.missing_ep_nos.length"
                                                  size="tiny" type="warning" :loading="retryingJobId === job.id"
                                                  @click.stop="retryJob(job, 'episodes')">重试漏集</n-button>
                                        <img v-if="job.poster_object_url" :src="job.poster_object_url" :alt="job.drama ? job.drama.title : ''"
                                             class="w-10 h-14 object-cover rounded" />
                                    </div>
                                </template>

                                <div class="space-y-5">
                                    <div v-if="job.translated_title" class="bg-gray-50 dark:bg-gray-800/50 p-4 rounded-lg">
                                        <div class="text-sm text-gray-500 dark:text-gray-400 mb-1">翻译后剧名</div>
                                        <p class="font-medium">{{ job.translated_title }}</p>
                                        <div class="text-sm text-gray-500 dark:text-gray-400 mt-3 mb-1">翻译后简介</div>
                                        <p class="text-sm text-gray-700 dark:text-gray-300 leading-relaxed">{{ job.translated_desc || '-' }}</p>
                                    </div>

                                    <n-collapse class="border rounded-lg">
                                        <n-collapse-item title="提示词与结果对照">
                                            <div class="space-y-4">
                                                <div>
                                                    <div class="text-sm text-gray-500 dark:text-gray-400 mb-1">① 翻译 System</div>
                                                    <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
                                                        <div class="bg-gray-50 dark:bg-gray-800/50 rounded p-3">
                                                            <div class="text-xs text-gray-400 mb-1">模板</div>
                                                            <pre class="text-xs overflow-auto max-h-48 whitespace-pre-wrap">{{ job.translate_system_prompt || '(默认)' }}</pre>
                                                        </div>
                                                        <div class="bg-blue-50/50 dark:bg-blue-900/20 rounded p-3">
                                                            <div class="text-xs text-gray-400 mb-1">最终值</div>
                                                            <pre class="text-xs overflow-auto max-h-48 whitespace-pre-wrap">{{ job.translate_system_prompt_final || '(尚未运行)' }}</pre>
                                                        </div>
                                                    </div>
                                                </div>

                                                <div>
                                                    <div class="text-sm text-gray-500 dark:text-gray-400 mb-1">② 翻译 User</div>
                                                    <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
                                                        <div class="bg-gray-50 dark:bg-gray-800/50 rounded p-3">
                                                            <div class="text-xs text-gray-400 mb-1">模板</div>
                                                            <pre class="text-xs overflow-auto max-h-48 whitespace-pre-wrap">{{ job.translate_user_prompt || '(默认)' }}</pre>
                                                        </div>
                                                        <div class="bg-blue-50/50 dark:bg-blue-900/20 rounded p-3">
                                                            <div class="text-xs text-gray-400 mb-1">最终值</div>
                                                            <pre class="text-xs overflow-auto max-h-48 whitespace-pre-wrap">{{ job.translate_user_prompt_final || '(尚未运行)' }}</pre>
                                                        </div>
                                                    </div>
                                                </div>

                                                <div>
                                                    <div class="text-sm text-gray-500 dark:text-gray-400 mb-1">③ 生图 Prompt</div>
                                                    <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
                                                        <div class="bg-gray-50 dark:bg-gray-800/50 rounded p-3">
                                                            <div class="text-xs text-gray-400 mb-1">模板</div>
                                                            <pre class="text-xs overflow-auto max-h-48 whitespace-pre-wrap">{{ job.image_prompt_template || '(默认)' }}</pre>
                                                        </div>
                                                        <div class="bg-blue-50/50 dark:bg-blue-900/20 rounded p-3">
                                                            <div class="text-xs text-gray-400 mb-1">最终值</div>
                                                            <pre class="text-xs overflow-auto max-h-48 whitespace-pre-wrap">{{ job.image_prompt_final || '(尚未运行)' }}</pre>
                                                        </div>
                                                    </div>
                                                </div>
                                            </div>
                                        </n-collapse-item>
                                    </n-collapse>

                                    <div v-if="job.poster_object_url">
                                        <div class="text-sm text-gray-500 dark:text-gray-400 mb-1">生成的新海报</div>
                                        <a :href="job.poster_object_url" target="_blank">
                                            <img :src="job.poster_object_url" :alt="job.translated_title || ''"
                                                 class="w-[120px] h-[160px] object-cover rounded-lg shadow hover:shadow-md transition" />
                                        </a>
                                    </div>
                                </div>
                            </n-collapse-item>
                        </n-collapse>
                    </n-card>
                </template>
            </page-shell>
        `,
    });
})();
