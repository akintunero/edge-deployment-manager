{{- define "edge-stack.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "edge-stack.fullname" -}}
{{- printf "%s-%s" .Release.Name (include "edge-stack.name" .) | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "edge-stack.labels" -}}
app.kubernetes.io/name: {{ include "edge-stack.name" . }}
helm.sh/chart: {{ .Chart.Name }}-{{ .Chart.Version }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end -}}
