# Infor Connector — UI component plan

Источники: `Docs/session-notes/UI_COMPONENT_VOCABULARY.md`, `UI_INTERFACE_STANDARD.md`,
`concepts/panels.md`. Основано на функционале `infor-connector`.

## 0. Разница с IDEAL_ONBOARDING.md
Идеал предполагает автоматическую пробу типичных health-эндпоинтов сразу после
подключения. Реализация делает это явно через отдельную кнопку "Test connection"
(вызывает `audit_infor_access` с фиксированным набором путей), а не автоматически при
сохранении формы — из-за отсутствия гарантии, что у SDK Form-компонента есть
пост-submit хук для второго вызова без участия пользователя.

## 1. Компоненты

| Экран | Примитивы | Почему именно эти |
|---|---|---|
| Sidebar (left) | `ui.Stack`(v, align="start") + `ui.Text`(tenant label) + `ui.Divider` + `ui.Button`("Open ION bridge") + `ui.Button`("App settings") | Без карточек, без дублирования инструкций. |
| Connect form (sidebar, not connected) | `ui.Form` + `ui.Select`(mode: "Paste .ionapi file" / "Enter fields manually") + labelled `ui.Textarea`(ionapi JSON) ИЛИ labelled `ui.Input`×5 (tenant/client id/secret/portal url/service account keys) + `ui.Button`("How do I get this?" → help dialog) | Select переключает режим ввода — оба реально нужны по Discovery. |
| Help dialog | `ui.Dialog`/`ui.panel(center_overlay=True)` + `ui.Text`(шаги получения .ionapi через ION Desk) + `ui.Alert`(type="warning", про партнёрскую документацию Infor) | Единственное место с инструкциями. |
| ION bridge (center, `center_overlay=True`) | `ui.Text`(subtitle "Generic ION API call") + `ui.Form`(action=call_ion_api: method Select, path Input, body Textarea) + `ui.Divider` + `ui.CodeBlock`(response JSON) | Прямой мост — путь и метод вводит сам пользователь, это соответствует Discovery (нет типизированных схем per-продукт). |
| Workflow tasks list | `ui.DataTable`(task id/subject/priority/due) + row action `ui.Button`("Open") | Табличный список, паттерн, использованный во всех связанных ERP/RPA коннекторах. |
| Workflow task detail | Back-button + `ui.KeyValue`(task fields) + `ui.Button`×3 (Approve/Reject/Complete, variant="primary"/"danger"/"secondary") | Явные раздельные кнопки действия, а не один Select — снижает риск случайного отклонения. |
| Document Flow messages list | `ui.DataTable`(message id/status/document type/timestamp) + row action `ui.Button`("Resend", variant="secondary") | Тот же паттерн списка. |
| App settings (center) | `ui.Header` + список подключений с `ui.Button`("Disconnect", variant="danger") | Единственное место для отключения, вынесено из сайдбара. |

## 2. Финальный список компонентов первой версии
`ui.Stack`, `ui.Text`, `ui.Divider`, `ui.Button`, `ui.Form`, `ui.Select`, `ui.Input`,
`ui.Textarea`, `ui.Dialog`/`ui.panel(center_overlay=True)`, `ui.Alert`, `ui.CodeBlock`,
`ui.DataTable`, `ui.KeyValue`, `ui.Header`.
