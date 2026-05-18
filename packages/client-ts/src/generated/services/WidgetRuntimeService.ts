/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class WidgetRuntimeService {
    /**
     * React shim — JavaScript module (not JSON)
     * Serve the React shim. Plugin widgets built with
     * --alias:react=/api/widget-runtime/react.js import from this URL.
     *
     * Returns a JavaScript module (`application/javascript`), not JSON —
     * `response_class=Response` is set so /openapi.json doesn't claim a
     * JSON schema for it.
     * @returns any React shim ESM module.
     * @throws ApiError
     */
    public static widgetRuntimeReact(): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/widget-runtime/react.js',
        });
    }
    /**
     * react/jsx-runtime shim — JavaScript module (not JSON)
     * Serve the react/jsx-runtime shim. esbuild --jsx=automatic emits
     * imports of jsx/jsxs/Fragment from `react/jsx-runtime`; this shim
     * rebinds them to the host's runtime.
     * @returns any react/jsx-runtime shim ESM module.
     * @throws ApiError
     */
    public static widgetRuntimeJsxRuntime(): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/widget-runtime/react-jsx-runtime.js',
        });
    }
}
