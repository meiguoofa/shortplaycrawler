/* global window, Vue */
(function () {
    'use strict';
    const { defineComponent, ref, computed, onMounted, h } = window.__appShared.Vue;
    const { apiGet, useNotify, JobStatusTag } = window.__appShared;
    const { usePoll } = window.__appShared;
    const { PageShell, EmptyState, LoadingSkeleton, ErrorState } = window.__appShared;

    window.JobList = defineComponent({
        components: { PageShell, EmptyState, LoadingSkeleton, ErrorState, JobStatusTag },
        setup() {
            const notify = useNotify();
            const loading = ref(true);
            const error = ref('');
            const jobs = ref([]);
            const statusFilter = ref('all');

            async function load(opts = {}) {
                const silent = opts.silent;
                if (!silent) loading.value = true;
                error.value = '';
                try {
                    const data = await apiGet('/api/daily-new/jobs');
                    jobs.value = data.jobs || [];
                } catch (e) {
                    if (!silent) error.value = e.message;
                    notify.error('加载失败: ' + e.message);
                } finally {
                    if (!silent) loading.value = false;
                }
            }
            onMounted(load);

            const filteredJobs = computed(() => {
                if (statusFilter.value === 'all') return jobs.value;
                if (statusFilter.value === 'pending') return jobs.value.filter(j => !['done', 'failed'].includes(j.status));
                return jobs.value.filter(j => j.status === statusFilter.value);
            });

            const stats = computed(() => ({
                total: jobs.value.length,
                done: jobs.value.filter(j => j.status === 'done').length,
                failed: jobs.value.filter(j => j.status === 'failed').length,
                pending: jobs.value.filter(j => !['done', 'failed'].includes(j.status)).length,
            }));

            const hasPending = computed(() => stats.value.pending > 0);
            usePoll(() => { if (hasPending.value) load({ silent: true }); }, 10000);

            const columns = computed(() => [
                { title: 'ID', key: 'id', width: 70, align: 'center' },
                {
                    title: '状态', key: 'status', width: 110, align: 'center',
                    render: (row) => h(JobStatusTag, { status: row.status, size: 'small' }),
                },
                { title: '剧名', key: 'drama.title', render: (r) => r.drama ? r.drama.title : '-', minWidth: 200 },
                { title: '语言', key: 'target_lang', width: 90, align: 'center' },
                { title: '翻译后', key: 'translated_title', minWidth: 200, render: (r) => r.translated_title || '-' },
                {
                    title: '海报', key: 'poster_object_url', width: 70, align: 'center',
                    render: (row) => row.poster_object_url ? h('a', { href: row.poster_object_url, target: '_blank' }, [
                        h('img', { src: row.poster_object_url, alt: row.translated_title || '', class: 'w-8 h-11 object-cover rounded mx-auto' })
                    ]) : '-',
                },
                { title: '剧集', key: 'ep', width: 90, align: 'center', render: (r) => `${r.uploaded_episodes}/${r.total_episodes}` },
                { title: '批次', key: 'batch_id', width: 120, render: (r) => r.batch_id ? h('n-text', { code: true, depth: 3 }, () => r.batch_id.slice(0, 8) + '...') : '-' },
                { title: '更新时间', key: 'updated_at', width: 160, render: (r) => window.__appShared.formatDateTime(r.updated_at) },
            ]);

            const filterTabs = [
                { label: '全部', value: 'all' },
                { label: '完成', value: 'done' },
                { label: '失败', value: 'failed' },
                { label: '运行中', value: 'pending' },
            ];

            function exportJobs(format) {
                const ids = filteredJobs.value.map(j => j.id).join(',');
                window.open('/api/daily-new/jobs/export?format=' + format + '&job_ids=' + ids, '_blank');
            }

            return { loading, error, jobs, filteredJobs, stats, statusFilter, columns, filterTabs, exportJobs, load };
        },
        template: `
            <page-shell title="翻译任务">
                <template #actions>
                    <div class="flex flex-wrap items-center gap-4">
                        <n-statistic label="总任务" :value="stats.total" />
                        <n-statistic label="完成" :value="stats.done" />
                        <n-statistic label="失败" :value="stats.failed" />
                        <n-statistic label="运行中" :value="stats.pending" />
                        <div class="flex gap-2">
                            <n-button type="success" size="small" @click="exportJobs('csv')">导出 CSV</n-button>
                            <n-button type="info" size="small" @click="exportJobs('xlsx')">导出 Excel</n-button>
                        </div>
                    </div>
                </template>

                <loading-skeleton v-if="loading" type="list" :rows="8" />
                <error-state v-else-if="error" :message="error" @retry="load" />
                <n-card v-else title="任务列表">
                    <template #header-extra>
                        <n-tabs v-model:value="statusFilter" type="line" size="small">
                            <n-tab v-for="t in filterTabs" :key="t.value" :name="t.value" :tab="t.label" />
                        </n-tabs>
                    </template>

                    <empty-state v-if="filteredJobs.length === 0" :title="statusFilter === 'all' ? '暂无任务' : '该状态下暂无任务'" />
                    <n-data-table v-else
                        :columns="columns"
                        :data="filteredJobs"
                        :pagination="{ pageSize: 30 }"
                        :scroll-x="1200"
                        size="medium"
                        striped
                    />
                </n-card>
            </page-shell>
        `,
    });
})();
