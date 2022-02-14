/**
 * Decorator that scrolls to specified coordinates of the page.
 *     Scrolling will occur after the wrapped function takes place (promise-friendly).
 * 
 * @param {number|Function} [top] - The y-value of the window to scroll to.
 *     If a function is given, it will be called with no arguments and the return value will be used.
 * @param {number|Function} [left] - The x-value of the window to scroll to.
 *     If a function is given, it will be called with no arguments and the return value will be used.
 * @param {ScrollBehavior} [behavior] - The scroll behavior that is used.
 * 
 * @decorator
 */
export function scrollTo(top?: number|Function, left?: number|Function, behavior?: ScrollBehavior): Function {
    return (target: any, propertyKey: string, descriptor: TypedPropertyDescriptor<any>): any => {
        const method = descriptor.value;
        descriptor.value = function(...args: any[]) {
            const res = method.apply(this, args);
            Promise.resolve(res).then(() => {
                if (typeof top === "function") top = top.apply(null) as number;
                if (typeof left === "function") left = left.apply(null) as number;
                window.scrollTo({ top, left, behavior });
            });
            return res;
        }
        return descriptor;
    }
}
/**
 * Decorator that scrolls to the top of the page using @scrollTo.
 * 
 * @see scrollTo
 * @decorator
 */
export function scrollToTop(left?: number|Function, behavior?: ScrollBehavior): Function {
    return scrollTo(0, left, behavior);
}