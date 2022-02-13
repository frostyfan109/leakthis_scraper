/**
 * Decorator that scrolls to the top of the page.
 * 
 * @decorator
 */
export function scrollTo(top?: number|Function, left?: number|Function, behavior?: ScrollBehavior): Function {
    return (target: any, propertyKey: string, descriptor: TypedPropertyDescriptor<any>): any => {
        const method = descriptor.value;
        descriptor.value = function(...args: any[]) {
            method.apply(this, args);
            if (typeof top === "function") top = top.apply(null) as number;
            if (typeof left === "function") left = left.apply(null) as number;
            window.scrollTo({ top, left, behavior });
        }
        return descriptor;
    }
}
export function scrollToTop(...args: any[]): Function {
    return scrollTo(0, ...args);
}