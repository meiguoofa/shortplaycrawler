/* global window, Vue */
(function () {
    'use strict';
    const { defineComponent, ref, computed, onMounted, h } = window.__appShared.Vue;
    const { apiGet, apiPost, apiDelete, substitute, useNotify, JobStatusTag } = window.__appShared;
    const { useConfigStore } = window.__appShared;
    const { useRouter } = window.__appShared.VueRouter;
    const { PageShell, EmptyState, LoadingSkeleton, ErrorState } = window.__appShared;

    window.PendingCart = defineComponent({
        components: { PageShell, EmptyState, LoadingSkeleton, ErrorState, JobStatusTag },
        setup() {
            const router = useRouter();
            const config = useConfigStore();
            const notify = useNotify();

            const loading = ref(true);
            const error = ref('');
            const items = ref([]);

            const targetLang = ref('en');
            const imageModel = ref('');
            const translateModel = ref('');
            const imagePrompt = ref('');
            const translateSystemPrompt = ref('');
            const translateUserPrompt = ref('');
            const descLang = ref('');
            const descModel = ref('');
            const descPrompt = ref('');

            async function load() {
                loading.value = true;
                error.value = '';
                try {
                    const data = await apiGet('/api/pending-cart');
                    items.value = data.items || [];
                } catch (e) {
                    error.value = e.message;
                    notify.error('加载失败: ' + e.message);
                } finally {
                    loading.value = false;
                }
            }

            onMounted(async () => {
                await config.load();
                if (!imageModel.value) imageModel.value = config.defaultImageModel;
                if (!translateModel.value) translateModel.value = config.defaultTranslateModel;
                if (!imagePrompt.value) imagePrompt.value = config.defaultImagePrompt;
                if (!translateSystemPrompt.value) translateSystemPrompt.value = config.defaultTranslateSystemPrompt;
                if (!translateUserPrompt.value) translateUserPrompt.value = config.defaultTranslateUserPrompt;
                if (!descLang.value) descLang.value = 'en';
                if (!descModel.value) descModel.value = config.defaultDescModel;
                if (!descPrompt.value) descPrompt.value = config.defaultDescPrompt;
                await load();
            });

            const langName = computed(() => config.langs[targetLang.value] || targetLang.value);
            const langOptions = computed(() => Object.entries(config.langs).map(
                ([code, name]) => ({ label: `${name} (${code})`, value: code })
            ));
            const imageModelOptions = computed(() => config.imageModels.map(
                m => ({ label: m, value: m })
            ));
            const translateModelOptions = computed(() => config.translateModels.map(
                m => ({ label: m, value: m })
            ));
            const descLangOptions = computed(() => Object.entries(config.descLangs).map(
                ([code, name]) => ({ label: `${name} (${code})`, value: code })
            ));
            const descModelOptions = computed(() => config.descModels.map(
                m => ({ label: m, value: m })
            ));
            const firstSelected = computed(() => items.value[0]);

            const finalTranslateSystem = computed(() =>
                substitute(translateSystemPrompt.value, { target_lang: langName.value })
            );
            const finalTranslateUser = computed(() => {
                const d = firstSelected.value;
                return substitute(translateUserPrompt.value, {
                    title: d ? d.title : '<清单为空时不可预览>',
                    description: d ? d.description || '' : '<清单为空时不可预览>',
                });
            });
            const finalImagePrompt = computed(() =>
                substitute(imagePrompt.value, {
                    target_lang: langName.value,
                    synopsis: '<翻译后填入>',
                })
            );
            const descLangName = computed(() => config.descLangs[descLang.value] || descLang.value);
            const finalDescPrompt = computed(() =>
                substitute(descPrompt.value, { target_lang: descLangName.value })
            );

            async function removeItem(id) {
                try {
                    await apiDelete('/api/pending-cart/' + id);
                    notify.success('已移除');
                    await load();
                } catch (e) {
                    notify.error('移除失败: ' + e.message);
                }
            }

            async function clearAll() {
                if (items.value.length === 0) return;
                if (!confirm(`确认清空清单中全部 ${items.value.length} 部剧？`)) return;
                try {
                    await apiDelete('/api/pending-cart/0');
                    notify.success('已清空');
                    await load();
                } catch (e) {
                    notify.error('清空失败: ' + e.message);
                }
            }

            const submitting = ref(false);
            async function submitCheckout() {
                if (items.value.length === 0) {
                    notify.warning('清单为空');
                    return;
                }
                submitting.value = true;
                try {
                    const data = await apiPost('/api/pending-cart/checkout', {
                        target_lang: targetLang.value,
                        image_model: imageModel.value,
                        image_prompt: imagePrompt.value,
                        translate_system_prompt: translateSystemPrompt.value,
                        translate_user_prompt: translateUserPrompt.value,
                        translate_model: translateModel.value,
                        desc_lang: descLang.value,
                        desc_model: descModel.value,
                        desc_prompt: descPrompt.value,
                    });
                    notify.success(`批次 ${data.batch_id.slice(0, 8)} 已提交，共 ${data.drama_ids.length} 部剧`);
                    setTimeout(() => router.push('/daily-new/batches/' + data.batch_id), 1000);
                } catch (e) {
                    notify.error('提交失败: ' + e.message);
                } finally {
                    submitting.value = false;
                }
            }

            const columns = computed(() => [
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
                    title: '简介', key: 'description', minWidth: 260,
                    render: (row) => h('div', {
                        class: 'max-w-[320px] truncate text-sm text-gray-600 dark:text-gray-300',
                        title: row.description || '',
                    }, row.description || '-'),
                },
                {
                    title: '操作', key: 'actions', width: 100, align: 'center',
                    render: (row) => h('n-button', {
                        size: 'small', type: 'error', ghost: true,
                        onClick: () => removeItem(row.id),
                    }, { default: () => '移除' }),
                },
            ]);

            const rowKey = (row) => row.id;

            return {
                loading, error, items,
                targetLang, imageModel, translateModel, imagePrompt,
                translateSystemPrompt, translateUserPrompt,
                descLang, descModel, descPrompt,
                config, langName, langOptions, imageModelOptions, translateModelOptions,
                descLangOptions, descModelOptions,
                finalTranslateSystem, finalTranslateUser, finalImagePrompt,
                finalDescPrompt, descLangName,
                columns, rowKey,
                submitting, submitCheckout,
                clearAll, load,
            };
        },
        template: `
            <page-shell title="待处理清单">
                <template #actions>
                    <n-button @click="load()">刷新</n-button>
                    <n-button v-if="items.length > 0" type="warning" ghost @click="clearAll">清空</n-button>
                </template>

                <loading-skeleton v-if="loading" type="list" :rows="4" />
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
                                    <div class="min-w-[220px] flex-1 max-w-md">
                                        <div class="text-sm text-gray-500 dark:text-gray-400 mb-1">翻译模型</div>
                                        <n-select v-model:value="translateModel" :options="translateModelOptions" />
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
                                            <div class="text-sm text-gray-500 dark:text-gray-400 pt-2">最终值（实时，取清单首项预览）</div>
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
                                    <n-tab-pane name="desc" tab="④ 截图描述">
                                        <div class="space-y-3">
                                            <div class="flex flex-wrap gap-4">
                                                <div class="min-w-[200px]">
                                                    <div class="text-sm text-gray-500 dark:text-gray-400 mb-1">描述语言（独立于翻译）</div>
                                                    <n-select v-model:value="descLang" :options="descLangOptions" />
                                                </div>
                                                <div class="min-w-[280px] flex-1 max-w-md">
                                                    <div class="text-sm text-gray-500 dark:text-gray-400 mb-1">视觉模型</div>
                                                    <n-select v-model:value="descModel" :options="descModelOptions" />
                                                </div>
                                                <div class="flex items-end">
                                                    <span class="text-xs text-gray-400">前 3 集各截 2 张（片长 1/3、2/3 处），共 6 张/剧</span>
                                                </div>
                                            </div>
                                            <div class="space-y-2">
                                                <div class="text-sm text-gray-500 dark:text-gray-400">模板 (可用 {target_lang})</div>
                                                <n-input v-model:value="descPrompt" type="textarea" :rows="4" />
                                                <div class="text-sm text-gray-500 dark:text-gray-400 pt-2">最终值（实时）</div>
                                                <n-input :value="finalDescPrompt" type="textarea" :rows="4" readonly />
                                            </div>
                                        </div>
                                    </n-tab-pane>
                                </n-tabs>
                            </div>
                        </n-collapse-item>
                    </n-collapse>

                    <n-card title="清单内容">
                        <empty-state v-if="items.length === 0" title="清单为空，请先去搜索页加入剧" />
                        <n-data-table v-else
                            :columns="columns"
                            :data="items"
                            :row-key="rowKey"
                            :pagination="{ pageSize: 20 }"
                            :scroll-x="1100"
                            size="medium"
                            striped
                        />
                    </n-card>
                </template>

                <!-- 底部 sticky 操作栏 -->
                <div v-if="items.length > 0" class="sticky bottom-0 left-0 right-0 bg-white/90 dark:bg-gray-800/90 backdrop-blur border-t dark:border-gray-700 shadow-lg p-4 -mx-4 md:-mx-6 lg:-mx-8">
                    <div class="max-w-7xl mx-auto flex flex-col md:flex-row items-center justify-between gap-3">
                        <div class="text-sm text-gray-600 dark:text-gray-300">
                            共 <strong>{{ items.length }}</strong> 部剧，目标语言 <strong>{{ langName }}</strong>
                        </div>
                        <n-button class="w-full md:w-auto" type="primary" size="large" :loading="submitting"
                                  @click="submitCheckout">
                            提交批次（写入每日上新 + 跑翻译/爬取）
                        </n-button>
                    </div>
                </div>
            </page-shell>
        `,
    });
})();
