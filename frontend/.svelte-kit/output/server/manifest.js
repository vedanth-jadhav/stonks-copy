export const manifest = (() => {
function __memo(fn) {
	let value;
	return () => value ??= (value = fn());
}

return {
	appDir: "_app",
	appPath: "_app",
	assets: new Set([]),
	mimeTypes: {},
	_: {
		client: {start:"_app/immutable/entry/start.D3eXURZ6.js",app:"_app/immutable/entry/app.cQGLn6ni.js",imports:["_app/immutable/entry/start.D3eXURZ6.js","_app/immutable/chunks/BH5D8ekw.js","_app/immutable/chunks/DlK7ccNx.js","_app/immutable/entry/app.cQGLn6ni.js","_app/immutable/chunks/DlK7ccNx.js","_app/immutable/chunks/Fl2vGg9w.js","_app/immutable/chunks/ft8FxlI5.js","_app/immutable/chunks/CyHlRNtF.js","_app/immutable/chunks/BfZ3Skjx.js"],stylesheets:[],fonts:[],uses_env_dynamic_public:false},
		nodes: [
			__memo(() => import('./nodes/0.js')),
			__memo(() => import('./nodes/1.js'))
		],
		remotes: {
			
		},
		routes: [
			
		],
		prerendered_routes: new Set(["/","/blotter","/command","/config","/gemini-oauth","/logs","/memory","/portfolio","/reports"]),
		matchers: async () => {
			
			return {  };
		},
		server_assets: {}
	}
}
})();
