/* global window, Vue */
(function () {
    'use strict';
    const { defineComponent, ref, reactive, computed, onMounted, watch, h } = window.__appShared.Vue;
    const { apiGet, apiPost, genBatchId, substitute, useNotify, JobStatusTag } = window.__appShared;
    const { useConfigStore } = window.__appShared;
    const { useRouter } = window.__appShared.VueRouter;
    const { usePoll } = window.__appShared;
    const { PageShell, EmptyState, LoadingSkeleton, ErrorState } = window.__appShared;

    window.DailyNew = defineComponent({
        components: { PageShell, EmptyState, LoadingSkeleton, ErrorState, JobStatusTag },
        setup() {
            const router = useRouter();
            const config = useConfigStore();
            const notify = useNotify();

            const loading = ref(true);
            const error = ref('');
            const dramas = ref([]);
            const jobMap = ref({});
            const targetDate = ref(new Date().toISOString().slice(0, 10));
            const prevDate = ref('');
            const nextDate = ref('');

            const targetLang = ref('en');
            const imageModel = ref('');
            const imagePrompt = ref('');
            const translateSystemPrompt = ref('');
            const translateUserPrompt = ref('');
            const selectedDramaIds = ref([]);

            // Backfill modal
            const backfillModal = ref(false);
            const backfillForm = reactive({ start_date: '2026-06-15', end_date: '' });
            const backfilling = ref(false);

            async function load(opts = {}) {
                const silent = opts.silent;
                if (!silent) loading.value = true;
                error.value = '';
                try {
                    const data = await apiGet('/api/daily-new?date=' + targetDate.value);
                    dramas.value = data.dramas || [];
                    jobMap.value = data.job_map || {};
                    targetDate.value = data.target_date;
                    prevDate.value = data.prev_date;
                    nextDate.value = data.next_date;
                    if (!backfillForm.end_date) backfillForm.end_date = data.target_date;
                } catch (e) {
                    if (!silent) error.value = e.message;
                    notify.error('加载失败: ' + e.message);
                } finally {
                    if (!silent) loading.value = false;
                }
            }

            onMounted(async () => {
                await config.load();
                if (!imageModel.value) imageModel.value = config.defaultImageModel;
                if (!imagePrompt.value) imagePrompt.value = config.defaultImagePrompt;
                if (!translateSystemPrompt.value) translateSystemPrompt.value = config.defaultTranslateSystemPrompt;
                if (!translateUserPrompt.value) translateUserPrompt.value = config.defaultTranslateUserPrompt;
                await load();
            });

            // 提示词实时预览
            const langName = computed(() => config.langs[targetLang.value] || targetLang.value);
            const langOptions = computed(() => Object.entries(config.langs).map(
                ([code, name]) => ({ label: `${name} (${code})`, value: code })
            ));
            const imageModelOptions = computed(() => config.imageModels.map(
                m => ({ label: m, value: m })
            ));
            const firstSelected = computed(() => {
                const id = selectedDramaIds.value[0];
                return dramas.value.find(d => d.id === id);
            });

            const finalTranslateSystem = computed(() =>
                substitute(translateSystemPrompt.value, { target_lang: langName.value })
            );
            const finalTranslateUser = computed(() => {
                const d = firstSelected.value;
                return substitute(translateUserPrompt.value, {
                    title: d ? d.title : '<勾选剧后填入>',
                    description: d ? d.description || '' : '<勾选剧后填入>',
                });
            });
            const finalImagePrompt = computed(() =>
                substitute(imagePrompt.value, {
                    target_lang: langName.value,
                    synopsis: '<翻译后填入>',
                })
            );

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
                        h('div', { class: 'text-xs text-gray-500 dark:text-gray-400 mt-0.5' }, `${row.author || '未知作者'} · ${row.category || '-'} · ${row.episode_cnt || 0} 集`),
                    ]),
                },
                { title: '分类', key: 'category', width: 100 },
                { title: '集数', key: 'episode_cnt', width: 80, align: 'center' },
                {
                    title: '简介', key: 'description', minWidth: 260,
                    render: (row) => h('div', {
                        class: 'max-w-[320px] truncate text-sm text-gray-600 dark:text-gray-300',
                        title: row.description || '',
                    }, row.description || '-'),
                },
                {
                    title: '已处理', key: 'jobs', width: 140, align: 'center',
                    render: (row) => {
                        const jobs = jobMap.value[String(row.id)] || [];
                        if (!jobs.length) return h('span', { class: 'text-gray-400 text-sm' }, '-');
                        return h('div', { class: 'flex flex-wrap justify-center gap-1' }, jobs.map(j =>
                            h(JobStatusTag, { key: j.id, status: j.status, size: 'small' })
                        ));
                    },
                },
            ]);

            const rowKey = (row) => row.id;

            // 提交处理
            const submitting = ref(false);
            async function submitRun() {
                if (selectedDramaIds.value.length === 0) {
                    notify.warning('请至少勾选一部剧');
                    return;
                }
                const batchId = genBatchId();
                submitting.value = true;
                try {
                    await apiPost('/api/daily-new/run', {
                        drama_ids: selectedDramaIds.value,
                        target_lang: targetLang.value,
                        image_model: imageModel.value,
                        image_prompt: imagePrompt.value,
                        translate_system_prompt: translateSystemPrompt.value,
                        translate_user_prompt: translateUserPrompt.value,
                        batch_id: batchId,
                        force_retry: false,
                    });
                    notify.success(`批次 ${batchId.slice(0, 8)} 已提交`);
                    setTimeout(() => router.push('/daily-new/batches'), 800);
                } catch (e) {
                    notify.error('提交失败: ' + e.message);
                } finally {
                    submitting.value = false;
                }
            }

            // 回填
            async function runBackfill() {
                if (!backfillForm.start_date || !backfillForm.end_date) {
                    notify.warning('请选择起止日期');
                    return;
                }
                backfilling.value = true;
                try {
                    const data = await apiPost('/api/daily-new/backfill', backfillForm);
                    notify.success(`回填完成: 共插入 ${data.total_inserted} 部剧`);
                    backfillModal.value = false;
                    await load();
                } catch (e) {
                    notify.error('回填失败: ' + e.message);
                } finally {
                    backfilling.value = false;
                }
            }

            // 自动刷新（有 pending 时 10s 刷新一次）
            const hasPending = computed(() =>
                Object.values(jobMap.value).some(jobs => jobs.some(j => !['done', 'failed'].includes(j.status)))
            );
            const { pause, resume } = usePoll(() => {
                if (hasPending.value) load({ silent: true });
            }, 10000);
            onMounted(() => resume());

            return {
                loading, error, dramas, jobMap, targetDate, prevDate, nextDate,
                targetLang, imageModel, imagePrompt,
                translateSystemPrompt, translateUserPrompt,
                selectedDramaIds,
                config, langName, firstSelected,
                langOptions, imageModelOptions,
                finalTranslateSystem, finalTranslateUser, finalImagePrompt,
                columns, rowKey,
                submitting, submitRun,
                backfillModal, backfillForm, backfilling, runBackfill,
                load,
            };
        },
        template: `
            <page-shell title="每日上新">
                <template #actions>
                    <div class="flex flex-wrap items-center gap-3">
                        <n-button @click="targetDate = prevDate; load()">← 上一日</n-button>
                        <n-date-picker v-model:formatted-value="targetDate" type="date" value-format="yyyy-MM-dd"
                                       style="width: 150px;" @update:formatted-value="load" />
                        <n-button @click="targetDate = nextDate; load()">下一日 →</n-button>
                        <n-button type="warning" ghost @click="backfillModal = true">📥 回填</n-button>
                    </div>
                </template>

                <loading-skeleton v-if="loading" type="list" :rows="6" />
                <error-state v-else-if="error" :message="error" @retry="load" />
                <template v-else>
                    <n-collapse class="mb-6">
                        <n-collapse-item title="提示词与模型设置">
                            <div class="space-y-4">
                                <div class="flex flex-wrap gap-4">
                                    <div class="min-w-[200px]">
                                        <div class="text-sm text-gray-500 dark:text-gray-400 mb-1">目标语言</div>
                                        <n-select v-model:value="targetLang" :options="langOptions" />
                                    </div>
                                    <div class="min-w-[280px] flex-1 max-w-md">
                                        <div class="text-sm text-gray-500 dark:text-gray-400 mb-1">生图模型</div>
                                        <n-select v-model:value="imageModel" :options="imageModelOptions" />
                                    </div>
                                    <div class="flex items-end">
                                        <span class="text-xs text-gray-400">可用变量: {target_lang} {synopsis} {title} {description}</span>
                                    </div>
                                </div>

                                <n-tabs type="line">
                                    <n-tab-pane name="translate-system" tab="① 翻译 System">
                                        <div class="space-y-2">
                                            <div class="text-sm text-gray-500 dark:text-gray-400">模板 (可用 {target_lang})</div>
                                            <n-input v-model:value="translateSystemPrompt" type="textarea" :rows="4" />
                                            <div class="text-sm text-gray-500 dark:text-gray-400 pt-2">最终值（实时）</div>
                                            <n-input :value="finalTranslateSystem" type="textarea" :rows="4" readonly />
                                        </div>
                                    </n-tab-pane>
                                    <n-tab-pane name="translate-user" tab="② 翻译 User">
                                        <div class="space-y-2">
                                            <div class="text-sm text-gray-500 dark:text-gray-400">模板 (可用 {title} {description})</div>
                                            <n-input v-model:value="translateUserPrompt" type="textarea" :rows="4" />
                                            <div class="text-sm text-gray-500 dark:text-gray-400 pt-2">最终值（实时，先勾选一部剧）</div>
                                            <n-input :value="finalTranslateUser" type="textarea" :rows="4" readonly />
                                        </div>
                                    </n-tab-pane>
                                    <n-tab-pane name="image" tab="③ 生图">
                                        <div class="space-y-2">
                                            <div class="text-sm text-gray-500 dark:text-gray-400">模板 (可用 {target_lang} {synopsis})</div>
                                            <n-input v-model:value="imagePrompt" type="textarea" :rows="4" />
                                            <div class="text-sm text-gray-500 dark:text-gray-400 pt-2">最终值（实时预览，{synopsis} 提交后填入实际译文）</div>
                                            <n-input :value="finalImagePrompt" type="textarea" :rows="4" readonly />
                                        </div>
                                    </n-tab-pane>
                                </n-tabs>
                            </div>
                        </n-collapse-item>
                    </n-collapse>

                    <n-card title="当日上新剧集">
                        <empty-state v-if="dramas.length === 0" title="当日暂无新剧" />
                        <n-data-table v-else
                            :columns="columns"
                            :data="dramas"
                            :row-key="rowKey"
                            v-model:checked-row-keys="selectedDramaIds"
                            :pagination="{ pageSize: 20 }"
                            :scroll-x="1100"
                            size="medium"
                            striped
                        />
                    </n-card>
                </template>

                <!-- 底部 sticky 操作栏 -->
                <div class="sticky bottom-0 left-0 right-0 bg-white/90 dark:bg-gray-800/90 backdrop-blur border-t dark:border-gray-700 shadow-lg p-4 -mx-4 md:-mx-6 lg:-mx-8">
                    <div class="max-w-7xl mx-auto flex flex-col md:flex-row items-center justify-between gap-3">
                        <div class="text-sm text-gray-600 dark:text-gray-300">
                            已选 <strong>{{ selectedDramaIds.length }}</strong> 部剧，目标语言 <strong>{{ langName }}</strong>
                        </div>
                        <n-button class="w-full md:w-auto" type="primary" size="large" :loading="submitting"
                                  :disabled="selectedDramaIds.length === 0" @click="submitRun">
                            开始处理（完整集数）
                        </n-button>
                    </div>
                </div>

                <!-- 回填 modal -->
                <n-modal v-model:show="backfillModal" preset="card" title="回填历史数据" style="width: 500px; max-width: 90vw;">
                    <p class="text-sm text-gray-600 dark:text-gray-400 mb-4">从接口拉取指定日期范围内所有日的上新剧。</p>
                    <div class="space-y-4">
                        <div>
                            <div class="text-sm text-gray-500 dark:text-gray-400 mb-1">起始日期</div>
                            <n-date-picker v-model:formatted-value="backfillForm.start_date" type="date" value-format="yyyy-MM-dd"
                                           style="width: 100%;" />
                        </div>
                        <div>
                            <div class="text-sm text-gray-500 dark:text-gray-400 mb-1">结束日期</div>
                            <n-date-picker v-model:formatted-value="backfillForm.end_date" type="date" value-format="yyyy-MM-dd"
                                           style="width: 100%;" />
                        </div>
                    </div>
                    <template #footer>
                        <div class="flex justify-end gap-2">
                            <n-button @click="backfillModal = false">取消</n-button>
                            <n-button type="primary" :loading="backfilling" @click="runBackfill">开始回填</n-button>
                        </div>
                    </template>
                </n-modal>
            </page-shell>
        `,
    });
})();
